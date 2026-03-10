    // PRINT 
    function printDiv(pdfdiv) {
        var printContents = document.getElementById(pdfdiv).innerHTML;
        var originalContents = document.body.innerHTML;
        
        // //hide and show elements
        // var $section = $(`#${pdfdiv}`).find('section'); 
        // $section.removeClass('hidden'); 
        // hide_elements(true) 

        
       
        // const element = document.getElementById(pdfdiv);  
        // // Add a footer element
        // const footer = document.createElement('div');
        // footer.style.textAlign = 'left';
        // footer.style.marginTop = '20px';
        // footer.innerHTML = '<p class="text-gray-700">{{note}}</p>'; // Customize your footer note here
        // element.appendChild(footer);

        document.body.innerHTML = printContents;
        window.print();
    
        document.body.innerHTML = originalContents;

        //  //hide and show elements
        //  setTimeout(() => {
        //     $section.addClass('hidden');
        //     hide_elements(false)
        //     element.removeChild(footer);
            
        // }, 0);
    }



    // DOWNLOAD AS PDF
    function generatePDF(div) {

        //hide and show elements
        var $section = $(`#${div}`).find('section'); 
        $section.removeClass('hidden'); 
        hide_elements(true) 

        
       
        const element = document.getElementById(div);  
        // Add a footer element
        const footer = document.createElement('div');
        footer.style.textAlign = 'left';
        footer.style.marginTop = '20px';
        footer.innerHTML = '<p class="text-gray-700">{{note}}</p>'; // Customize your footer note here
        element.appendChild(footer);

        html2pdf(element, {
            margin: 10,
            filename: 'report.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            }).then(function (pdf) {
                
            // You can save or display the generated PDF as needed
            pdf.save();
        });
        
        
        //hide and show elements
        setTimeout(() => {
            $section.addClass('hidden');
            hide_elements(false)
            element.removeChild(footer);
            
        }, 0);
    }

    function printPDF() {
        generatePDF();
        // var printWindow = window.open(",",'width=800,height=600');
        // printWindow.document.write(element.innerHTML);
        // printWindow.document.close();
        // printWindow.print()
    }
    function Email_AS_PDF(div) {
        
        email_modal.showModal()
        $("#div").val(div)


    }
    
    function Email_PDF(div) {
        
            // hide and show elements
            var $section = $(`#${div}`).find('section');
            $section.removeClass('hidden');
            hide_elements(true)

            const element = document.getElementById(div);
            const email = document.getElementById('email').value;
          
            const opt = {
                margin: [10, 10, 10, 10],  // [top, left, bottom, right] margins in mm
                filename: 'document.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2 },  // Increase the canvas resolution
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };

            // Convert the HTML content to PDF and apply options
            html2pdf().set(opt).from(element).toPdf().get('pdf').then(function (pdf) {
                // Convert PDF to Blob
                const pdfBlob = pdf.output('blob');

                // Prepare FormData to send PDF via AJAX
                const formData = new FormData();
                formData.append('pdf_file', pdfBlob, 'document.pdf');
                formData.append('email', email );
                
                // Send PDF to backend via AJAX
                fetch('/send_email_with_pdf', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}',  // Add CSRF token
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (div === "sq"){
                            alert('Quote sent successfully!');
                        }
                    } else {
                        alert('Error sending PDF: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            });

            //hide and show elements
            setTimeout(() => {
                $section.addClass('hidden');
                hide_elements(false)
                
            }, 0);
    }


    // DOWNLOAD AS EXCEL
    function downloadExcel() {
        window.location.href = "{% url 'report:generate_excel' %}";
    }

    function printTable(pdfdiv) {
        window.print();
    }
    function convertTableToExcel(tableId, table_data) {
        var table = $('#' + tableId);
        var filename = table_data;
        var excelHtml = table.clone().appendTo('body');
        excelHtml.find('button, input, textarea').remove();
        var excelFile = excelHtml.html();
        excelHtml.remove();
        var uri = 'data:application/vnd.ms-excel;charset=utf-8,' + encodeURIComponent(excelFile);
        var link = document.createElement('a');
        link.href = uri;
        link.download = filename + '.xls';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
function exportTableToExcel(table_id) {
        removeElementById();
       
        // Get the table data
        var table = document.getElementById(`${table_id}`);
        var rows = table.querySelectorAll('tr');
        var data = [];
    
        rows.forEach(row => {                                                                  
            var cells = row.querySelectorAll('td, th');
            var rowData = [];
            cells.forEach(cell => {
                rowData.push(cell.innerText);
            });
            data.push(rowData);
        });
    
       // Get headings and totals
    //var heading = document.querySelector('p.hhh').innerText;
    // var totalSales = document.getElementById('sales_total').innerText;
    // var totalExpenses = document.getElementById('purchase_total').innerText;
    // var balance = document.getElementById('total').innerText;
   
    // Send the data to the server
    fetch('{% url "report:export_sales_report" %}', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({
            table_data: data,
            //heading: heading,
            // total_sales: totalSales,
            // total_expenses: totalExpenses,
            // balance: balance
        })
    })
        .then(response => response.blob())
        .then(blob => {
            // Create a link to download the file
            var link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = 'sales_report.xlsx';
            document.body.appendChild(link); // Append to the body to make sure it works in some browsers
            link.click();
            document.body.removeChild(link); // Clean up after download
        });
    }