let lastKnownScrollPosition = 0;
let ticking = false;

function doSomething(scrollPos) {
  console.log(scrollPos)
}

document.addEventListener('scroll', function(e) {
  lastKnownScrollPosition = window.scrollY;

  if (!ticking) {
    window.requestAnimationFrame(function() {
      doSomething(lastKnownScrollPosition);
      ticking = false;
    });

    ticking = true;
  }
});