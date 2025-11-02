document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#etf-form");
    const tableBody = document.querySelector("#etf-table tbody");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const etfs = document.querySelector("#etfs").value;
        const period = document.querySelector("#period").value;

        tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;">Loading...</td></tr>`;

        try {
            const response = await fetch(`/api/etf_harris?etfs=${etfs}&period=${period}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Clear existing rows
            tableBody.innerHTML = "";

            // Populate table
            data.forEach(etfData => {
                const row = document.createElement("tr");

                row.innerHTML = `
                    <td>${etfData.ticker}</td>
                    <td>${etfData.nav_return?.toFixed(2) || 'N/A'}%</td>
                    <td>${etfData.underlying_return?.toFixed(2) || 'N/A'}%</td>
                    <td>${etfData.distribution_return?.toFixed(2) || 'N/A'}%</td>
                    <td>${etfData.total_return?.toFixed(2) || 'N/A'}%</td>
                    <td>${etfData.return_of_capital_percentage}</td>
                    <td>${etfData.harris_factor?.toFixed(2) || 'N/A'}</td>
                `;
                tableBody.appendChild(row);
            });

        } catch (error) {
            console.error("Error fetching ETF data:", error);
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:red;">Error loading data. See console for details.</td></tr>`;
        }
    });
});
