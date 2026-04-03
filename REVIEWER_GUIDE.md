# ASTRON | Advanced SQL Intelligence Platform (Reviewer Guide)

Welcome to **ASTRON**, a state-of-the-art, sharded microservice mesh designed for hyper-scale SQL observability and autonomous optimization.

---

## 1. Provisioning a New Instance (Organization)

To simulate a fresh enterprise deployment, follow these steps in the ASTRON Gateway:

1.  **Access the Gateway**: Visit [http://localhost:8000/dashboard/index.html](http://localhost:8000/dashboard/index.html).
2.  **Provision Instance**: Click **"New Organization? Provision Instance →"** at the bottom of the access portal.
3.  **Configure**:
    *   **Instance ID**: Enter a unique organization handle (e.g., `enterprise-lab-01`).
    *   **Organization Legal Name**: Enter your corporate name (e.g., `Reviewer Strategic Labs`).
4.  **Capture Credentials**: Click **"Provision Secure Shard"**.
    *   The system will instantly architect a dedicated PostgreSQL database for this instance.
    *   An **API ACCESS TOKEN** will be displayed in the obsidian box. **Copy this credentials hash immediately.**
5.  **Secure Login**: Return to the access portal and use your new **Instance ID** and **Access Token**.

---

## 2. Seeding Enterprise Telemetry

After logging in, your dashboard will be empty. To seed it with sharded query intelligence:

1.  **Open your terminal** at the project root.
2.  **Execute the Mesh Seed**:
    ```bash
    # Replace <YOUR_INSTANCE_ID> with your provisioned ID
    python3 exporters/demo_exporter.py --tenant <YOUR_INSTANCE_ID>
    ```
3.  **Synchronize Dashboard**: Return to the UI. Your monitor will now heartbeat with real-time query clusters and intelligent lineage maps.

---

## 3. Auditing the Intelligence Discovery

1.  **Review**: Click any row in the **Discovery Table**.
2.  **Discovery Hub**: The side panel will slide out, performing an asynchronous fetch for **Intelligent Lineage Analysis** and **Optimization Recommendations**.
3.  **Analyze Shard Integrity**: Click the **"EXECUTE OPTIMIZATION PLAN"** button. This triggers a cinematic simulation of the platform's autonomous management vision.
4.  **Secure Logout**: Click **"Secure Logout"** in the sidebar to verify session integrity.

---

## 4. Architectural Verification

- **Enterprise Schema**: View the sharded route table at [http://localhost:8000/v1/openapi.json](http://localhost:8000/v1/openapi.json).
- **Service Mesh Health**: Check mesh liveness at [http://localhost:8000/health](http://localhost:8000/health).

**ASTRON is now ready for Audit Convergence.**
