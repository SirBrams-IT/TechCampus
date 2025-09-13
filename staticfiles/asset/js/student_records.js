    function openDeleteModal(deleteUrl) {
        document.getElementById('confirmDeleteBtn').href = deleteUrl;
        var deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        deleteModal.show();
    }
    
    function populateEditForm(id, name, email, username, phone, id_number, date_of_birth, gender) {
        document.getElementById("student_id").value = id;
        document.getElementById("student_name").value = name;
        document.getElementById("student_email").value = email;
        document.getElementById("student_username").value = username;
        document.getElementById("student_phone").value = phone;
        document.getElementById("student_id_number").value = id_number;
        document.getElementById("student_dob").value = date_of_birth;
        document.getElementById("student_gender").value = gender;

        document.getElementById("editStudentForm").addEventListener("submit", function(event) {
            event.preventDefault(); // Prevent default form submission

            let form = this;
            let formData = new FormData(form);

            fetch("{% url 'edit_student' %}", {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    // Show error message inside modal
                    let errorDiv = document.getElementById("editStudentError");
                    errorDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                } else if (data.success) {
                    // Reload the page after a short delay for changes to reflect
                    window.location.reload();
                }
            })
            .catch(error => console.error("Error:", error));
        });
    }
    
    function printStudentList() {
        // Create a print-friendly version of the student list
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>Student List - SirBrams Tech Virtual Campus</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h2 { color: #0d6efd; text-align: center; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f8f9fa; }
                    .header { text-align: center; margin-bottom: 20px; }
                    .print-date { text-align: right; margin-bottom: 10px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>SirBrams Tech Virtual Campus</h2>
                    <h3>Registered Students List</h3>
                </div>
                <div class="print-date">Printed on: ${new Date().toLocaleDateString()}</div>
                <table>
                    <thead>
                        <tr>
                            <th>S/N</th>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Username</th>
                            <th>Phone</th>
                            <th>ID No</th>
                            <th>DOB</th>
                            <th>Gender</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for x in page_obj %}
                        <tr>
                            <td>{{ forloop.counter0|add:page_obj.start_index }}</td>
                            <td>{{ x.name }}</td>
                            <td>{{ x.email }}</td>
                            <td>{{ x.username }}</td>
                            <td>{{ x.phone }}</td>
                            <td>{{ x.id_number }}</td>
                            <td>{{ x.date_of_birth }}</td>
                            <td>{{ x.gender }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => {
            printWindow.print();
            printWindow.close();
        }, 250);
    }
