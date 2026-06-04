# 🚀 Beginner-Friendly Deployment Guide

This guide walks you through deploying the **Nusantara Context-Aware Recommendation A/B Lab** from scratch. 

We will set up:
1.  **MotherDuck:** Serverless database to store your data.
2.  **GitHub Actions:** Weekly automated pipeline to run the ingestion & transformations.
3.  **GCP e2-micro VM:** Free virtual machine to host the Apache Superset dashboard.

---

## 📋 Prerequisites
Before starting, ensure you have:
*   A [GitHub Account](https://github.com/) with this repository cloned or forked.
*   A [Google Cloud Platform (GCP)](https://cloud.google.com/) account.
*   A [MotherDuck Account](https://motherduck.com/) (free tier).
*   [Terraform](https://developer.hashicorp.com/terraform/downloads) installed on your local computer.
*   [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) installed on your local computer.

---

## 🛠️ Step 1: Get Your MotherDuck Token
1.  Log in to [MotherDuck](https://motherduck.com/).
2.  Click on the **cog icon (Settings)** in the top right corner.
3.  Click **Copy token** next to your MotherDuck Token.
4.  Save this token somewhere safe (e.g., in a password manager). You will need it in later steps.

---

## ☁️ Step 2: Deploy GCP Infrastructure with Terraform
We use Terraform to automatically create the virtual machine (VM) and set up the network firewall.

### 1. Authenticate with Google Cloud
Open your computer's terminal and log in to your GCP account:
```bash
gcloud auth application-default login
```
This opens a web browser. Log in and authorize permissions.

### 2. Run Terraform
Navigate to the folder where you cloned this repository, and run these commands:
```bash
# Initialize Terraform (downloads the Google Cloud provider)
terraform init

# Plan the creation (reviews what resources will be created)
terraform plan -var="gcp_project_id=YOUR_GCP_PROJECT_ID"

# Apply the creation (actually builds the VM on GCP)
terraform apply -var="gcp_project_id=YOUR_GCP_PROJECT_ID"
```
*Note: Replace `YOUR_GCP_PROJECT_ID` with your actual GCP Project ID (visible in your GCP Console).*

When prompted, type `yes` and press **Enter**.

### 3. Record the VM External IP
Once finished, Terraform will output the VM's public IP address:
```bash
vm_external_ip = "35.224.X.X"
```
Copy this IP address down. You will use it to access your dashboard.

---

## 🤖 Step 3: Configure GitHub Actions secrets
To automate the weekly ingestion and transformation runs, configure GitHub to securely access MotherDuck.

1.  Open your repository on **GitHub**.
2.  Click on the **Settings** tab at the top.
3.  On the left-hand sidebar, expand **Secrets and variables** and click **Actions**.
4.  Click the green **New repository secret** button.
5.  Set the fields:
    *   **Name:** `MOTHERDUCK_TOKEN`
    *   **Secret:** Paste your MotherDuck token (copied in Step 1).
6.  Click **Add secret**.
7.  **(Optional Test):** Click the **Actions** tab at the top of your GitHub repository, select **Indonesian Recommendation Friction ETL Pipeline** on the left, click **Run workflow**, and press the green button to trigger a manual test run of the ingestion!

---

## 🐳 Step 4: Run Apache Superset on the GCP VM
Now we SSH into our newly created VM, clone the repository, and start Apache Superset.

### 1. SSH into the VM
Run this command in your local terminal:
```bash
gcloud compute ssh superset-dashboard-vm --zone=us-central1-a
```

### 2. Clone the Code and Launch the Dashboard
Once connected to the VM terminal, run:
```bash
# Clone your repository
git clone https://github.com/YOUR_GITHUB_USERNAME/nusantara-context-ab-lab.git

# Enter the project directory
cd nusantara-context-ab-lab

# Start Apache Superset using Docker Compose
sudo docker compose up --build -d
```
*(The initialization script will automatically download the Docker images, build the custom Superset driver, run database migrations, and create the admin user)*.

---

## 📊 Step 5: Connect Apache Superset to MotherDuck
1.  Open your web browser and navigate to `http://<VM_EXTERNAL_IP>:8088` (replace with your VM's public IP).
2.  Log in with:
    *   **Username:** `admin`
    *   **Password:** `admin` *(Highly recommended: Change this immediately by clicking on your profile in the top-right!)*
3.  In the top menu, go to **Settings** > **Database Connections**.
4.  Click the **+ Database** button in the top right.
5.  Choose **DuckDB** from the dropdown menu. If it's not visible, choose **Other** and configure:
    *   **Display Name:** `MotherDuck Lab`
    *   **SQLAlchemy URI:** 
        ```text
        duckdb:///md:recommendation_lab?token=YOUR_MOTHERDUCK_TOKEN
        ```
        *(Replace `YOUR_MOTHERDUCK_TOKEN` with the token from Step 1)*.
6.  Click **Connect** followed by **Save**.

🎉 **Congratulations!** Your pipeline is now fully running, automated, and connected to your visualization dashboard. You can now build charts querying the `marts` schema!
