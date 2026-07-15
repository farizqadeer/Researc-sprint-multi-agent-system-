# main.py
from flask import Flask, request, jsonify, render_template
from research_pipeline import run_pipeline
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)

# Store results in memory (use Redis in production)
pipeline_results = {}
pipeline_status = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/research", methods=["POST"])
def research():
    data = request.json
    topic = data.get("topic", "").strip()
    
    if not topic:
        return jsonify({"error": "Please enter a topic"}), 400
    
    job_id = f"job_{len(pipeline_results) + 1}"
    pipeline_status[job_id] = "running"
    
    # Run pipeline in background thread so Flask does not hang
    def run_in_background():
        try:
            result = run_pipeline(topic)
            pipeline_results[job_id] = result
            pipeline_status[job_id] = "complete"
        except Exception as e:
            pipeline_status[job_id] = f"error: {str(e)}"
# ADD timeout watchdog — if job runs more than 3 minutes, mark as error
    import time

    def watchdog():
        time.sleep(180)  # wait 3 minutes
        if job_id in jobs and jobs[job_id]["status"] == "running":
            jobs[job_id]["status"] = "error"
            jobs[job_id]["result"] = {"error": "Pipeline timed out after 3 minutes. Try a simpler topic."}
    thread = threading.Thread(target=run_in_background)
    thread.start()
    
    return jsonify({"job_id": job_id, "status": "running"})

@app.route("/status/<job_id>")
def check_status(job_id):
    status = pipeline_status.get(job_id, "not_found")
    
    if status == "complete":
        return jsonify({
            "status": "complete",
            "result": pipeline_results.get(job_id)
        })
    
    return jsonify({"status": status})

if __name__ == "__main__":
    app.run(debug=True, port=5002)