# OpportunityShield

OpportunityShield is a FastAPI app for reviewing internship and job offers for
potential warning signs. Its risk score is a heuristic, not a probability or a
guarantee that an opportunity is genuine or fraudulent.

## Run locally

Install [Ollama](https://ollama.com/) and download the default model:

```powershell
ollama pull gemma3:1b
```

Then, from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>.

## Deploy to Render

The included `render.yaml` defines the web service. Push this repository to
GitHub, sign in to [Render](https://render.com/), choose **New** > **Blueprint**,
and connect this repository. Render will build and start the app from the
blueprint; its public URL appears in the service dashboard.

The web service cannot use Ollama running on your computer. For AI analysis in
the deployed app, configure `OLLAMA_HOST` in the Render service environment to
point to an Ollama server reachable from Render, and make sure the configured
model is installed there. Keep that Ollama endpoint private or protected; do not
publish an unauthenticated model server. Without a reachable Ollama server,
the site and preliminary local checks can run, but AI analysis will report an
error rather than a successful assessment.

Render's free web service may sleep when idle. Public visitors can submit text
to the deployed app, so avoid submitting sensitive personal or financial
information.
# Trail
