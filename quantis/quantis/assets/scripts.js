document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');

    var checkElements = setInterval(function() {
        var left = document.getElementById('left');
        var right = document.getElementById('right');

        if (left && right) {
            console.log('Elements found:', left, right);
            dragula([left, right],{
                moves: function (el, container, handle) {
                  return handle.classList.contains('handle');
                }});
            console.log('dragula called');
            clearInterval(checkElements); // Stop checking once elements are found
        } else {
            console.log('Elements not found yet, retrying...');
        }
    }, 100);

    var checkElements2 = setInterval(function() {
        var toggles = document.querySelectorAll('[data-toggle]')
        if (toggles.length > 0) {
            console.log(toggles)
            toggles.forEach(function(toggle) {
                console.log("Example toggle", toggle);
                toggle.addEventListener('click', function() {
                    console.log("Click!")
                    const contentId = this.getAttribute('data-toggle');
                    const content = document.querySelector(`[data-content="${contentId}"]`);
                    if (content.style.display === 'none') {
                        content.style.display = 'block';
                        content.parentNode.style.padding = '1em';
                    } else {
                        content.style.display = 'none';
                        content.parentNode.style.padding = '0em 1em';
                    }
                });
            });
            console.log('Toggles found');
            clearInterval(checkElements2)
        } else {
            console.log('Elements not found yet, retrying...');
        }
    }, 100);
});