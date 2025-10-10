from flask import Flask, jsonify, render_template
from etf_calculator import get_all_etf_data

app = Flask(__name__)

ETFS = ["COYY", "TSYY", "NVYY", "COII", "COIW", "ULTY", "MSII", "XBTY", "MST", "USOY", "HOOW", "YETH", "NVDW", "TSLW", "PLTW", "LFGY"]
ETFS = sorted(list(set(ETFS)))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/etfs")
def etf_data():
    app.logger.info("Request received for /api/etfs")
    # Convert list to tuple to make it hashable for caching
    all_etf_data = get_all_etf_data(tuple(ETFS))
    app.logger.info("Finished processing all ETFs")
    return jsonify(all_etf_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
