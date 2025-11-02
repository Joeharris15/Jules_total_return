from flask import Flask, jsonify, render_template, request
from etf_calculator import get_etf_data_with_harris_factor

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/etf_harris")
def etf_harris_data():
    app.logger.info("Request received for /api/etf_harris")
    etfs = request.args.get('etfs')
    period = request.args.get('period', type=int)

    if not etfs or not period:
        return jsonify({"error": "Missing 'etfs' or 'period' parameters."}), 400

    etf_list = [etf.strip().upper() for etf in etfs.split(',')]

    all_etf_data = get_etf_data_with_harris_factor(tuple(etf_list), period)
    app.logger.info("Finished processing all ETFs")

    # Sort the data by Harris Factor
    sorted_data = sorted(all_etf_data.values(), key=lambda x: x.get('harris_factor', 0), reverse=True)

    return jsonify(sorted_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
