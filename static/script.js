document.addEventListener("DOMContentLoaded", () => {
    const tableBody = document.querySelector("#etf-table tbody");

    async function fetchEtfData() {
        try {
            const response = await fetch("/api/etfs");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Clear existing rows
            tableBody.innerHTML = "";

            // Populate table
            for (const etf in data) {
                const row = document.createElement("tr");
                const etfData = data[etf];

                row.innerHTML = `
                    <td>${etf}</td>
                    <td>${etfData.current_price?.toFixed(2) || 'N/A'}</td>
                    <td>${etfData.one_month_return?.toFixed(2) || 'N/A'}%</td>
                    <td>${etfData.two_month_return?.toFixed(2) || 'N/A'}%</td>
                `;
                tableBody.appendChild(row);
            }
        } catch (error) {
            console.error("Error fetching ETF data:", error);
            tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:red;">Error loading data. See console for details.</td></tr>`;
        }
    }

    fetchEtfData();
});
