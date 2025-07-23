document.addEventListener('DOMContentLoaded', function () {
    const printBtn = document.getElementById('print-orders');
    const pdfClienteInput = document.getElementById('pdf-cliente');
    const pdfOrdineInput = document.getElementById('pdf-ordine');
    const pdfDataInput = document.getElementById('pdf-data');
    const pdfRowsBody = document.getElementById('pdf-rows-body');
    const toggleAllBtn = document.getElementById('toggle-select-all');
    const confirmPrintBtn = document.getElementById('confirm-print');

    function printOrder(cliente, ordine, data, rowsData) {
  const htmlContent = `
    <html>
    <head>
      <title>Ordine Cliente - ${ordine}</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        h1 { color: #0b2e61; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #0b2e61; color: white; }
        .header-info { margin-bottom: 20px; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #666; text-align: right; }
      </style>
    </head>
    <body>
      <h1>Ordine Cliente</h1>
      <div class="header-info">
        <div><strong>Ordine N.:</strong> ${ordine}</div>
        <div><strong>Cliente:</strong> ${cliente}</div>
        <div><strong>Data consegna:</strong> ${data}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>n. riga</th>
            <th>cod. articolo</th>
            <th>old code</th>
            <th>descrizione</th>
            <th>q.tà</th>
            <th>note produzione</th>
          </tr>
        </thead>
        <tbody>
          ${rowsData.map(row => `
            <tr>
              ${row.map(cell => `<td>${cell}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
      <div class="footer">
        ${data} - Pagina 1 di 1
      </div>
    </body>
    </html>
  `;

  const printWindow = window.open('', '', 'width=800,height=600');
  printWindow.document.write(htmlContent);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
  // Optional: printWindow.close();
}


    let allSelected = false;

    printBtn.addEventListener('click', () => {
      const visibleRows = Array.from(document.querySelectorAll('#sortable-table tbody tr'))
                                .filter(row => row.style.display !== 'none');

      // Prende cliente e ordine dalla prima riga visibile
      const firstRow = visibleRows[0];
      const cliente = firstRow.children[0].textContent.trim();
      const ordine = firstRow.children[3].textContent.trim();
      const data = firstRow.children[2].textContent.trim();

      pdfClienteInput.value = cliente;
      pdfOrdineInput.value = ordine;
      pdfDataInput.value = data;

      // Svuota righe precedenti
      pdfRowsBody.innerHTML = '';

      // Popola righe
      visibleRows.forEach(row => {
        const cells = row.children;
        const nRiga = cells[4].textContent.trim();
        const articolo = cells[7].textContent.trim();
        const oldCode = cells[8].textContent.trim();
        const desArticolo = cells[9].textContent.trim();
        const qtaOrd = cells[14].textContent.trim();
        const operatore = cells[6].textContent.trim();

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>
            <div class="form-check">
              <input class="form-check-input toggle-row" type="checkbox" checked data-selected="true" />
            </div>
          </td>
          <td>${nRiga}</td>
          <td>${articolo}</td>
          <td>${oldCode}</td>
          <td>${desArticolo}</td>
          <td>${qtaOrd}</td>
          <td>${operatore}</td>
        `;
        pdfRowsBody.appendChild(tr);
      });

    });

    // Toggle selezione singola riga
    pdfRowsBody.addEventListener('click', (e) => {
      if (e.target.classList.contains('toggle-row')) {
        const checkbox = e.target;
        const selected = checkbox.dataset.selected === 'true';
        checkbox.dataset.selected = (!selected).toString();

        // Ottieni tutte le checkbox
        const checkboxes = pdfRowsBody.querySelectorAll('.toggle-row');

        const allDeselected = Array.from(checkboxes).every(cb => !cb.checked);
        const allAreSelected = Array.from(checkboxes).every(cb => cb.checked);

        if (allAreSelected) {
          toggleAllBtn.textContent = 'Deseleziona tutte le righe';
          allSelected = true;
        } else if (allDeselected) {
          toggleAllBtn.textContent = 'Seleziona tutte le righe';
          allSelected = false;
        }
        else {
          toggleAllBtn.textContent = 'Deseleziona tutte le righe';
          allSelected = true;
        }
      }
    });

    // Seleziona/Deseleziona tutte le righe
    toggleAllBtn.addEventListener('click', () => {
      const allBtns = pdfRowsBody.querySelectorAll('.toggle-row');
      allSelected = !allSelected;
      toggleAllBtn.textContent = allSelected ? 'Deseleziona tutte le righe' : 'Seleziona tutte le righe';

      allBtns.forEach(checkbox => {
        checkbox.checked = allSelected;
        checkbox.dataset.selected = allSelected.toString();

        //checkbox.classList.toggle('active', allSelected);
      });

    });

    // Stampa solo righe selezionate
    confirmPrintBtn.addEventListener('click', () => {
      const selectedRows = [];
      pdfRowsBody.querySelectorAll('tr').forEach(row => {
        const btn = row.querySelector('.toggle-row');
        if (btn.dataset.selected === 'true') {
          const data = Array.from(row.children).slice(1).map(td => td.textContent.trim());
          selectedRows.push(data);
        }
      });

      if (selectedRows.length === 0) {
        alert("Seleziona almeno una riga da stampare.");
        return;
      }

      const cliente = pdfClienteInput.value;
      const ordine = pdfOrdineInput.value;
      const data = pdfDataInput.value;

      printOrder(cliente, ordine, data, selectedRows);
    });
  });

 