(function() {
    var domain = window.location.origin;
    var qr = new QRious({
      element: document.getElementById('qr'),
      value: `${domain}/validate/{{key}}`,
      size: 300,
      level: 'H'
    });
  })();


document.addEventListener('DOMContentLoaded', function() {

});