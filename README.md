Tournament Management Web App

A lightweight Flask web application for managing tournaments and participants with YAML-based data storage. Optimized for mobile devices, it offers modern UI elements and an intuitive user interface.

Features
	•	Multi-Day Tournaments: Single or multi-day events.
	•	Participant Status: Daily selection of Registered, Interested, or Not Attending.
	•	Edit/Update: Participants can modify their registrations afterward.
	•	Admin Mode: Protected by a static password to delete tournaments and participants.
	•	Detail Panel: Optional link and multi-line description for each tournament.
	•	Auto-Completion: Name suggestions based on previous entries.
	•	Date Picker: Calendar input for start and end dates.
	•	Responsive Design: One tournament per row, scrollable tables for many dates.
	•	CI/CD Pipeline: GitHub Actions for tests and automated Docker image build & push to Docker Hub.

⸻

Requirements
	•	Python 3.12+
	•	pip
	•	Docker (for container deployment)
	•	Git & GitHub (for CI/CD)

⸻

Installation & Local Setup
	1.	Clone the Repository

git clone https://github.com/<user>/tournament-management.git
cd tournament-management


	2.	Create a Virtual Environment

python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows


	3.	Install Dependencies

pip install --upgrade pip
pip install -r requirements.txt


	4.	Initialize the Data File

cp example/data.yaml .  # Copy sample data


	5.	Run the App

flask run --host=0.0.0.0 --port=5000

Access the application at http://localhost:5000

⸻

Docker
	1.	Build the Docker Image

docker build -t tournament-management .


	2.	Run the Container

docker run -p 5000:5000 -v $(pwd)/data.yaml:/app/data.yaml tournament-management



⸻

CI/CD with GitHub Actions

Workflow file: .github/workflows/ci-cd.yml
	•	Jobs:
	1.	test: Run pytest smoke tests for the Flask API
	2.	build-and-push: On merge to main, build Docker image & push to Docker Hub
	•	GitHub Secrets:
	•	DOCKERHUB_USERNAME
	•	DOCKERHUB_TOKEN

⸻

Git Configuration

# Set Git user globally
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"


⸻

.gitignore

Includes common Python/IDE artifacts, data.yaml, and excludes workflow files to keep the repo clean.

⸻