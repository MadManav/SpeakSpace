// Loader functionality
window.addEventListener('load', function() {
    const loader = document.getElementById('loader');
    loader.classList.add('loader-hidden');
});

// User photo upload functionality
const photoUpload = document.getElementById('photoUpload');
const userPhoto = document.getElementById('userPhoto');

photoUpload.addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            userPhoto.src = e.target.result;
        }
        reader.readAsDataURL(file);
    }
});

// Trigger file upload when clicking on the profile picture
userPhoto.parentElement.addEventListener('click', function() {
    photoUpload.click();
});