# CloudOps AI

> An AI-powered cloud operations assistant for infrastructure monitoring, incident detection, investigation, and safe cloud operations.

CloudOps AI is a final-year project designed to assist DevOps and cloud engineers in monitoring infrastructure, detecting incidents, investigating operational problems, and generating recommendations.

The project combines **React, FastAPI, PostgreSQL, AWS, and LangGraph** to create an intelligent cloud operations platform.

---

## Features

### Infrastructure Monitoring

- Monitor infrastructure servers.
- Display server status and CPU utilization.
- Identify running and stopped servers.
- Calculate infrastructure health statistics.
- Automatically refresh monitoring data.

### Incident Detection

CloudOps AI detects infrastructure problems based on configured conditions.

Current incident types include:

- High CPU utilization
- Medium CPU utilization
- Stopped servers

Incidents are assigned severity levels such as:

- Low
- Medium
- High
- Critical

### Incident History

Detected incidents are stored in PostgreSQL.

The system records:

- Incident ID
- Server
- Incident type
- Severity
- Incident message
- Detection time
- Resolution time
- Diagnosis
- Recommendation
- Investigation time

The system also prevents duplicate active incidents for the same server and incident type.

### AI Investigation

CloudOps AI includes a LangGraph-based incident investigation workflow.

Current capabilities include:

- Incident investigation
- Rule-based diagnosis
- Recommendation generation
- Investigation result persistence
- Fallback handling when an external AI model is unavailable

### AWS Integration

CloudOps AI integrates with AWS for infrastructure monitoring.

Current capabilities include:

- AWS connection testing
- EC2 instance discovery
- EC2 CPU monitoring
- CloudWatch integration
- AWS region configuration
- Read-only AWS monitoring

### Dashboard

The React dashboard provides:

- Infrastructure summary
- Running server count
- Stopped server count
- Active incident count
- CPU utilization
- AWS connection status
- Incident history
- Incident severity
- Incident status
- AI investigation results
- Recommended actions

---

## System Architecture

```text
                         CloudOps AI
                              |
              +---------------+---------------+
              |                               |
        React Frontend                  FastAPI Backend
              |                               |
              |                    +----------+----------+
              |                    |                     |
              |                Monitoring          Incident
              |                    |                Detection
              |                    |                     |
              |                    +----------+----------+
              |                               |
              |                         LangGraph AI
              |                               |
              |                         Investigation
              |                               |
              +-------------------------------+
                                              |
                                     PostgreSQL Database
                                              |
                                  +-----------+-----------+
                                  |                       |
                              Incidents                History
                              & Results
                                             
                                      |
                                      v
                                    AWS
                                      |
                               EC2 / CloudWatch
```

---

## Technology Stack

### Frontend

- React
- Vite
- JavaScript
- CSS

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### AI

- LangGraph
- LangChain
- Google Gemini integration
- Rule-based fallback

### Database

- PostgreSQL
- Psycopg

### Cloud

- Amazon Web Services (AWS)
- Amazon EC2
- Amazon CloudWatch
- AWS CLI
- Boto3

### Development Tools

- Git
- GitHub
- VSCodium / Neovim
- Linux

---

## Project Structure

```text
cloudops-ai/
│
├── backend/
│   ├── agents/
│   │   └── incident_agent.py
│   │
│   ├── aws_monitor.py
│   ├── database.py
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── ...
│   │
│   ├── package.json
│   └── ...
│
├── .env
├── .env.example
├── .gitignore
├── README.md
└── .venv/
```

---

## Requirements

Before running CloudOps AI, install:

- Python 3.11+
- Node.js
- npm
- PostgreSQL
- Git
- AWS CLI

An AWS account is required for AWS monitoring functionality.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Snd3sh/cloudops_ai.git
cd cloudops-ai
```

---

## Backend Setup

### 2. Create a Python Virtual Environment

```bash
python -m venv .venv
```

### Fish Shell

```fish
source .venv/bin/activate.fish
```

### Bash

```bash
source .venv/bin/activate
```

---

### 3. Install Python Dependencies

If `requirements.txt` is available:

```bash
pip install -r requirements.txt
```

Otherwise, install the required packages:

```bash
pip install fastapi uvicorn psycopg[binary] boto3 python-dotenv langgraph langchain-google-genai
```

---

## PostgreSQL Setup

Create the database:

```bash
sudo -u postgres psql
```

Inside PostgreSQL:

```sql
CREATE DATABASE cloudops_ai;
```

Exit PostgreSQL:

```sql
\q
```

The backend uses the following database:

```text
cloudops_ai
```

The required incident history table is automatically initialized when the backend starts.

---

## Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
AI_MODE=rules
```

For GitHub, provide an `.env.example` file instead:

```env
GEMINI_API_KEY=
GEMINI_MODEL=
AI_MODE=rules
```

### Important

Never commit `.env`, API keys, AWS credentials, or other secrets to GitHub.

Recommended `.gitignore` entries:

```gitignore
.venv/
__pycache__/
.env
.env.*
!.env.example
.aws/
node_modules/
dist/
```

---

## AWS Configuration

Configure the AWS CLI:

```bash
aws configure
```

Check the configured region:

```bash
aws configure get region
```

Test AWS authentication:

```bash
aws sts get-caller-identity
```

CloudOps AI uses AWS monitoring functionality with a read-only approach during development.

The project is designed to avoid unnecessary AWS resource creation during development and testing.

---

## Running the Backend

From the project root:

```bash
source .venv/bin/activate
```

For Fish:

```fish
source .venv/bin/activate.fish
```

Start FastAPI:

```bash
uvicorn backend.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Running the Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## API Endpoints

### Dashboard

```http
GET /api/dashboard
```

Returns infrastructure summary information.

### Monitoring

```http
GET /api/monitoring
```

Returns current infrastructure monitoring information.

### Incident History

```http
GET /api/incidents/history
```

Returns active and historical incidents.

### AI Investigation

```http
POST /api/ai/investigate/{server_id}
```

Investigates an incident for a specified server and stores the investigation result in PostgreSQL.

Example:

```text
/api/ai/investigate/server-002
```

### AWS Instances

```http
GET /api/aws/instances
```

Retrieves EC2 instance information from AWS.

### AWS CPU Monitoring

```http
GET /api/aws/cpu/{instance_id}
```

Retrieves CPU utilization information for an EC2 instance.

### CPU Simulation

```http
POST /api/simulation/cpu
```

Used during development to simulate CPU changes and test incident detection.

Example:

```json
{
  "server_id": "server-001",
  "cpu_usage": 95
}
```

### Server Status Simulation

```http
POST /api/simulation/status
```

Used during development to test server status changes.

---

## Incident Lifecycle

CloudOps AI follows this incident lifecycle:

```text
Infrastructure Monitoring
          |
          v
   Incident Detected
          |
          v
   Incident Recorded
          |
          v
    AI Investigation
          |
          v
 Diagnosis + Recommendation
          |
          v
   Incident Resolved
          |
          v
   Historical Record
```

When an incident is active, its `resolved_at` field remains `NULL`.

When the infrastructure recovers, CloudOps AI records the resolution timestamp.

If the same problem happens again later, a new incident record is created instead of reopening the previous resolved incident.

---

## AI Investigation

The current investigation workflow is built using LangGraph.

```text
Incident
   |
   v
Investigation Agent
   |
   v
Analyze Incident
   |
   +------> Diagnosis
   |
   +------> Recommendation
   |
   v
PostgreSQL
```

The project currently supports a rule-based investigation mode.

For example:

```text
CPU >= 80%
      |
      v
HIGH CPU INCIDENT
      |
      v
Diagnosis:
Server has high CPU utilization.

Recommendation:
Inspect running processes, application logs,
and recent traffic changes.
```

This provides a reliable baseline while the project is expanded toward a more advanced multi-agent architecture.

---

## Duplicate Incident Prevention

CloudOps AI prevents multiple active incidents of the same type from being created for the same server.

Example:

```text
Server: server-001
Incident: HIGH_CPU

Active Incident
      |
      +---- Dashboard Refresh
      |
      +---- Dashboard Refresh
      |
      +---- Dashboard Refresh
                |
                v
        Same Active Incident
```

After recovery:

```text
HIGH_CPU
   |
   v
RESOLVED
```

If the same problem occurs again:

```text
HIGH_CPU
   |
   v
New Incident ID
```

This allows the system to maintain a proper historical record of incidents.

---

## Security Considerations

CloudOps AI follows several security principles:

- AWS credentials are not stored in source code.
- `.env` is excluded from Git.
- API keys are stored using environment variables.
- AWS monitoring uses read-only access during development.
- Database credentials should not be committed to GitHub.
- Infrastructure-changing operations will require explicit approval.
- Automated remediation will be designed with human approval and verification.

---

## Current Project Status

### Implemented

- [x] React dashboard
- [x] FastAPI backend
- [x] PostgreSQL integration
- [x] Infrastructure monitoring
- [x] Simulated infrastructure
- [x] Incident detection
- [x] Incident history
- [x] Incident resolution tracking
- [x] Duplicate active-incident prevention
- [x] LangGraph investigation workflow
- [x] Rule-based AI investigation
- [x] Investigation persistence
- [x] AWS connection
- [x] AWS EC2 discovery
- [x] AWS CloudWatch CPU monitoring
- [x] CPU simulation for testing

---

## Roadmap

CloudOps AI is being developed in the following stages.

### 1. Multi-Agent AI

Build specialized LangGraph agents for:

- Incident diagnosis
- Root-cause analysis
- Log analysis
- Infrastructure analysis
- Recommendation generation
- Investigation coordination

Planned workflow:

```text
Incident
   |
   v
Coordinator Agent
   |
   +----> Monitoring Agent
   |
   +----> Diagnosis Agent
   |
   +----> Root Cause Agent
   |
   +----> Recommendation Agent
   |
   v
Final Investigation
```

---

### 2. AWS Cost Analysis

Planned capabilities:

- AWS resource cost analysis
- Identify potentially unused resources
- Cost trend analysis
- Resource-level cost information
- Cost optimization recommendations

---

### 3. Security Analysis

Planned capabilities:

- AWS security configuration checks
- IAM analysis
- Network configuration analysis
- Security group analysis
- Public resource detection
- Security recommendations

---

### 4. Safe Automated Remediation

Planned workflow:

```text
Problem Detected
       |
       v
AI Recommendation
       |
       v
Human Approval
       |
       +---- No ----> Cancel
       |
      Yes
       |
       v
Execute Remediation
       |
       v
Verify Result
       |
       v
Record Action
```

The system will not automatically perform potentially dangerous infrastructure changes without an approval mechanism.

---

### 5. Advanced Dashboard

Planned improvements:

- Infrastructure health charts
- CPU and resource trends
- Cost analytics
- Security findings
- AI investigation timeline
- Agent activity
- Remediation history
- Cloud resource overview
- Infrastructure health score

---

### 6. Deployment

The final version will be prepared for deployment with:

- Production frontend
- Production backend
- Environment variable management
- Secure API configuration
- PostgreSQL deployment
- AWS integration
- Authentication
- Production monitoring

---

## Future Architecture

The long-term goal is to evolve CloudOps AI into an intelligent cloud operations platform.

```text
                         CLOUDOPS AI
                              |
        +---------------------+---------------------+
        |                     |                     |
    Monitoring             Security               Cost
        |                     |                     |
        v                     v                     v
   Detection Agent      Security Agent        Cost Agent
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                       AI Coordinator
                              |
                              v
                       Investigation
                              |
                              v
                       Recommendation
                              |
                              v
                       Human Approval
                              |
                              v
                         Remediation
                              |
                              v
                         Verification
                              |
                              v
                          PostgreSQL
                              |
                              v
                          Dashboard
```

---

## Development

Clone the repository:

```bash
git clone https://github.com/Snd3sh/cloudops_ai.git
cd cloudops-ai
```

Create the virtual environment:

```bash
python -m venv .venv
```

Activate it:

```fish
source .venv/bin/activate.fish
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn backend.main:app --reload
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## Contributing

CloudOps AI is currently being developed as a final-year academic project.

Future improvements may include:

- Additional cloud providers
- More AI agents
- Advanced incident detection
- Security analysis
- Cost optimization
- Automated remediation
- Infrastructure-as-code integration
- Kubernetes monitoring

---

## Disclaimer

CloudOps AI is an educational and development project.

AWS infrastructure changes can incur costs and may affect cloud resources. Always use appropriate permissions, testing environments, and approval mechanisms before executing infrastructure changes.

The current project primarily uses simulated infrastructure for development and testing.

---

## Author

**Sandesh**

Final Year Project — CloudOps AI

GitHub:  
https://github.com/Snd3sh/cloudops_ai

---

## License

This project is currently intended for educational and academic purposes.
