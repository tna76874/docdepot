function adjustFooterSpace() {
    const footerHeight = document.querySelector('footer').offsetHeight;
    document.body.style.paddingBottom = footerHeight + 10 + 'px';
}

function disableButton() {
    var downloadButton = document.getElementById("downloadButton");
    downloadButton.classList.add("disabled");

    setTimeout(function() {
        downloadButton.classList.remove("disabled");
    }, 10000);
}

function openCheckLogOverlay(data) {
    var checkLogOverlay = document.createElement('div');
    checkLogOverlay.id = 'checkLogOverlay';

    var checkLogContent = document.createElement('div');
    checkLogContent.id = 'checkLogContent';

    var closeButton = document.createElement('span');
    closeButton.className = 'closeButton';
    closeButton.textContent = 'X';
    closeButton.addEventListener('click', function() {
        document.body.removeChild(checkLogOverlay);
    });

    var errorList = document.createElement('ul');
    errorList.style.textAlign = 'justify';
    errorList.style.padding = '0';
    errorList.style.listStyleType = 'none';

    data.forEach(function(check) {
        var listItem = document.createElement('li');
        var iconClass = '';
        if (check.passed === true) {
            iconClass = 'fa fa-check-circle text-success';
            iconColor = 'green';
        } else if (check.passed === false) {
            iconClass = 'fa fa-times-circle text-danger';
            iconColor = 'red';
        } else {
            iconClass = 'fa fa-question-circle text-warning';
            iconColor = 'orange';
        }
        var icon = document.createElement('i');
        icon.className = iconClass;
        icon.style.marginRight = '5px';
        icon.style.color = iconColor;

        var boldShort = document.createElement('span');
        boldShort.style.fontWeight = 'bold';
        boldShort.textContent = check.short;

        var text = document.createTextNode(': ' + check.description);
        listItem.appendChild(icon);
        listItem.appendChild(boldShort);
        listItem.appendChild(text);
        errorList.appendChild(listItem);
    });

    checkLogContent.appendChild(closeButton);
    checkLogContent.appendChild(errorList);
    checkLogOverlay.appendChild(checkLogContent);
    document.body.appendChild(checkLogOverlay);

    checkLogOverlay.style.display = 'block';
}

function handleFileUpload() {
        var fileInput = document.getElementById('fileInput');
        var uploadLabel = document.getElementById('uploadLabel');
        var spinnerOverlay = document.getElementById('spinnerOverlay');
        
        if (fileInput) {
            fileInput.addEventListener('change', function(event) {
                var file = event.target.files[0];
                if (file) {
                    var formData = new FormData();
                    formData.append('file', file);
                    formData.append('token', '{{ token }}');

                    uploadLabel.classList.add('disabled');
                    spinnerOverlay.style.display = 'flex';

                    fetch('/api/add_attachment', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        var errorItems = data.filter(item => item.passed === false);
                        
                        if (errorItems.length > 0) {
                            var errorDescriptions = errorItems.map(item => item.description).join('\n');
                            alert('Fehler:\n' + errorDescriptions);
                            openCheckLogOverlay(data);
                        } else {
                            location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Fehler beim Hochladen!');
                    })
                    .finally(() => {
                        uploadLabel.classList.remove('disabled');
                        spinnerOverlay.style.display = 'none';
                    });
                }
            });
        }
    }

document.addEventListener('DOMContentLoaded', function() {
    adjustFooterSpace()
    handleFileUpload()
});