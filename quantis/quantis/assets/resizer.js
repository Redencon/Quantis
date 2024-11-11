// Query the element

var checkElements = setInterval(function() {
    const resizer = document.getElementById('dragMe');
    
    if (resizer) {
            console.log('Elements found:', resizer);
            const leftSide = resizer.previousElementSibling;
            const rightSide = resizer.nextElementSibling;
            
            let x = 0;
            let y = 0;
            let leftWidth = 0;
            const mouseDownHandler = function (e) {
                // Get the current mouse position
                x = e.clientX;
                y = e.clientY;
                leftWidth = leftSide.getBoundingClientRect().width;
            
                // Attach the listeners to `document`
                document.addEventListener('mousemove', mouseMoveHandler);
                document.addEventListener('mouseup', mouseUpHandler);
            };
            
            const mouseUpHandler = function () {
                resizer.style.removeProperty('cursor');
                document.body.style.removeProperty('cursor');
            
                leftSide.style.removeProperty('user-select');
                leftSide.style.removeProperty('pointer-events');
            
                rightSide.style.removeProperty('user-select');
                rightSide.style.removeProperty('pointer-events');
            
                // Remove the handlers of `mousemove` and `mouseup`
                document.removeEventListener('mousemove', mouseMoveHandler);
                document.removeEventListener('mouseup', mouseUpHandler);
            };
            
            const mouseMoveHandler = function (e) {
                // How far the mouse has been moved
                const dx = e.clientX - x;
                const dy = e.clientY - y;
                // const newLeftWidth = ((leftWidth + dx) * 100) / resizer.parentNode.getBoundingClientRect().width
                const newLeftWidth = Math.min(Math.max((
                    ((leftWidth + dx) * 100) / resizer.parentNode.getBoundingClientRect().width
                ), 20), 80);
                leftSide.style.width = `${newLeftWidth}%`;
                document.body.style.cursor = 'col-resize';
                leftSide.style.userSelect = 'none';
                leftSide.style.pointerEvents = 'none';
            
                rightSide.style.userSelect = 'none';
                rightSide.style.pointerEvents = 'none';
            };

            resizer.addEventListener('mousedown', mouseDownHandler);
            clearInterval(checkElements);

        } else {
            console.log('Elements not found yet, retrying...');
        }
}, 100);
