document.addEventListener('DOMContentLoaded', function() {
    // Photo upload handling
    const photoUpload = document.getElementById('photoUpload');
    const userPhoto = document.getElementById('userPhoto');
    const profileContainer = document.querySelector('.profile-container');

    if (profileContainer) {
        profileContainer.addEventListener('click', () => {
            photoUpload.click();
        });
    }

    if (photoUpload) {
        photoUpload.addEventListener('change', function(e) {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    userPhoto.src = e.target.result;
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
});