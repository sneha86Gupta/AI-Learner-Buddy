document.addEventListener("DOMContentLoaded", function () {
    const registerForm = document.getElementById("registerForm");

    if (registerForm) {
        registerForm.addEventListener("submit", function (event) {
            event.preventDefault(); // Stop form submission initially

            const name = document.getElementById("name").value.trim();
            const username = document.getElementById("username").value.trim();
            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            const age = document.getElementById("age").value.trim();
            const profession = document.getElementById("profession").value;

            // Name validation: alphabets and spaces only
            const nameRegex = /^[A-Za-z\s]+$/;
            if (!nameRegex.test(name)) {
                alert("❌ Name should contain only alphabets and spaces.");
                return;
            }

            // Username validation: alphanumeric only
            const usernameRegex = /^[a-zA-Z0-9]+$/;
            if (!usernameRegex.test(username)) {
                alert("❌ Username must be alphanumeric.");
                return;
            }

            // Email validation
            if (!email.includes("@")) {
                alert("❌ Invalid email address.");
                return;
            }

            // Profession selection validation
            if (profession === "") {
                alert("❌ Please select a profession.");
                return;
            }

            // Password length
            if (password.length < 6) {
                alert("❌ Password must be at least 6 characters.");
                return;
            }

            // Age validation
            if (isNaN(age) || age <= 0) {
                alert("❌ Age must be a positive number.");
                return;
            }

            // If all validations pass, submit the form
            registerForm.submit();
        });
    }
});
