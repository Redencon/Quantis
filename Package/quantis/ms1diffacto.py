"""
Compiling data for diffacto run, running diffacto

Functions used by ms1+diffacto pipeline
"""
import pandas as pd
from subprocess import run
import os
from typing import NamedTuple, TypedDict, Literal

DiffactoNormMethod = Literal['average','median','GMM','None']


class DiffactoInputFiles(NamedTuple):
    peptides: str
    samples: str


class DiffactoOutput(str):
    @classmethod
    def from_dir(cls, outdir: str) -> 'DiffactoOutput':
        return DiffactoOutput(os.path.join(outdir, 'diffacto_out.txt'))


class DiffactoParameters(TypedDict):
    normalize: DiffactoNormMethod
    impute_threshold: float
    min_samples: int


def are_files_present(file: str) -> bool:
    suffixes = ["_proteins.tsv", "_PFMs_ML.tsv", "_PFMs.tsv"]
    for suf in suffixes:
        if file.endswith(suf):
            prefix = file.strip(suf)
            break
    else:
        return False
    for suf in suffixes:
        if not os.path.exists(prefix + suf):
            return False
    return True


def compile_diffacto_data(sample1: list[str], sample2: list[str], outdir: str) -> DiffactoInputFiles:
    sample_file = os.path.join(outdir, 'samples.txt')
    peptides_file = os.path.join(outdir, 'peptides.txt')
    replace_label = '_proteins.tsv'
    
    df_final = None

    allowed_prots = set()
    allowed_peptides = set()
    allowed_prots_all = set()

    all_labels = []

    for sample in (sample1, sample2):
        for z in sample:
            df0 = pd.read_table(z)
            allowed_prots.update(df0['dbname'])

    for sample in (sample1, sample2):
        for z in sample:
            df0 = pd.read_table(z.replace('_proteins.tsv', '_PFMs_ML.tsv'))
            df0 = df0[df0['qpreds'] <= 10]
            allowed_peptides.update(df0['seqs'])

    # for num, sample in zip(('S1', 'S2'), (sample1, sample2)):
    for sample in (sample1, sample2):
        if sample:
            for z in sample:
                df3 = pd.read_table(z.replace('_proteins.tsv', '_PFMs.tsv'))
                df3 = df3[df3['sequence'].apply(lambda x: x in allowed_peptides)]

                df3_tmp = df3[df3['proteins'].apply(lambda x: any(z in allowed_prots for z in x.split(';')))]
                for dbnames in set(df3_tmp['proteins'].values):
                    for dbname in dbnames.split(';'):
                        allowed_prots_all.add(dbname)

    for sample in (sample1, sample2):
        for z in sample:
            label = z.replace(replace_label, '')
            all_labels.append(label)
            df3 = pd.read_table(z.replace(replace_label, '_PFMs.tsv'))  # read PFMs

            df3 = df3[df3['proteins'].apply(lambda x: any(z in allowed_prots_all for z in x.split(';')))]
            df3['proteins'] = df3['proteins'].apply(lambda x: ';'.join([z for z in x.split(';') if z in allowed_prots_all]))

            df3['origseq'] = df3['sequence']
            df3['sequence'] = df3['sequence'] + df3['charge'].astype(int).astype(str) + df3['ion_mobility'].astype(str)

            df3 = df3.sort_values(by='Intensity', ascending=False)
            df3 = df3.drop_duplicates(subset='sequence')
            # df3 = df3.explode('proteins')

            df3[label] = df3['Intensity']
            df3['protein'] = df3['proteins']
            df3['peptide'] = df3['sequence']
            df3 = df3[['origseq', 'peptide', 'protein', label]]

            if df_final is None:
                df_final = df3.reset_index(drop=True)
            else:
                df_final = df_final.reset_index(drop=True).merge(df3.reset_index(drop=True), on='peptide', how='outer')
                df_final['protein_x'].fillna(value=df_final['protein_y'], inplace=True)
                df_final['origseq_x'].fillna(value=df_final['origseq_y'], inplace=True)
                df_final['protein'] = df_final['protein_x']
                df_final['origseq'] = df_final['origseq_x']

                df_final = df_final.drop(columns=['protein_x', 'protein_y'])
                df_final = df_final.drop(columns=['origseq_x', 'origseq_y'])

    assert df_final is not None
    df_final['intensity_median'] = df_final[all_labels].median(axis=1)
    df_final['nummissing'] = df_final[all_labels].isna().sum(axis=1)
    df_final = df_final.sort_values(by=['nummissing', 'intensity_median'], ascending=(True, False))
    df_final = df_final.drop_duplicates(subset=('origseq', 'protein'))
    df_final = df_final.set_index('peptide')
    df_final['proteins'] = df_final['protein']
    df_final = df_final.drop(columns=['protein'])
    cols = df_final.columns.tolist()
    cols.remove('proteins')
    cols.insert(0, 'proteins')
    df_final = df_final[cols]
    df_final.fillna(value='')
    df_final.to_csv(peptides_file, sep=',')
    
    with open(sample_file, 'w') as out:
        for num, sample in zip(('S1', 'S2'), (sample1, sample2)):
            for z in sample:
                label = z.replace(replace_label, '')
                out.write(label + '\t' + num + '\n') 
    return DiffactoInputFiles(peptides_file, sample_file)


def run_diffacto(input: DiffactoInputFiles, diffacto_path: str, parameters: DiffactoParameters, outdir: str) -> DiffactoOutput:
    out = DiffactoOutput.from_dir(outdir)
    run([
        diffacto_path, '-i', input.peptides, '-s', input.samples, '-o', out,
        '-normalize', parameters['normalize'],
        '-impute_threshold', str(parameters['impute_threshold']),
        '-min_samples', str(parameters['min_samples'])
    ], check=True)
    return out