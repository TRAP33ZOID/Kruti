window.addEventListener('DOMContentLoaded', (event) => {
    var uploadButton = document.getElementById('uploadButton');
    if (uploadButton) {
        uploadButton.onclick = function() {
            var form = document.getElementById('uploadForm');
            var formData = new FormData(form);
            var loading = document.getElementById('loading');
        
            loading.style.display = 'block'; // Show loading indicator
        
            fetch('/summarize', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                // The line below is commented out to prevent displaying the extracted text.
                // document.getElementById('extractedText').innerText = data.extractedText;
                document.getElementById('summaryOutput').innerText = data.summary;
                loading.style.display = 'none'; // Hide loading indicator
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('summaryOutput').innerText = 'Error summarizing text.';
                loading.style.display = 'none'; // Hide loading indicator
            });
        };
    }
});
