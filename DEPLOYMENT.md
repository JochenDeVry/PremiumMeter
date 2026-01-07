# PremiumMeter Deployment Guide for Portainer

This guide explains how to deploy the PremiumMeter webapp on your NAS using Portainer, with automatic deployment from your GitHub repository.

## Prerequisites

1. **Portainer installed** on your NAS
2. **GitHub repository** containing your code
3. **NAS IP address** (e.g., `192.168.1.100`)
4. **Docker and Docker Compose** available in Portainer

## Step 1: Push Code to GitHub

First, ensure all production files are committed and pushed:

```bash
git add .
git commit -m "Add production deployment configuration"
git push origin main
```

## Step 2: Prepare Environment Variables

You'll need these environment variables (replace with your values):

| Variable | Example | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | `SecurePass123!` | Database password |
| `SECRET_KEY` | `your-secret-key-min-32-chars` | Backend JWT secret |
| `VITE_API_URL` | `http://192.168.1.100:8000/api` | API endpoint for frontend |
| `ALLOWED_ORIGINS` | `http://192.168.1.100:3000` | CORS allowed origins |

**Generate a secure SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 3: Deploy in Portainer

### Using Portainer UI:

1. **Log in to Portainer** (usually at `http://YOUR_NAS_IP:9000`)

2. **Navigate to Stacks** → **Add Stack**

3. **Choose "Git Repository" method**

4. **Configure Repository:**
   - **Repository URL**: `https://github.com/YOUR_USERNAME/PremiumMeter`
   - **Repository reference**: `refs/heads/main`
   - **Compose path**: `docker-compose.portainer.yml`

5. **Add Environment Variables:**
   Click "Add an environment variable" for each:
   ```
   POSTGRES_PASSWORD=your_secure_password
   SECRET_KEY=your_secret_key_here
   VITE_API_URL=http://YOUR_NAS_IP:8000/api
   ALLOWED_ORIGINS=http://YOUR_NAS_IP:3000
   ```

6. **Enable Auto-Update (Optional):**
   - Toggle "Enable webhook" to get a URL
   - Add this URL to GitHub webhooks to auto-deploy on push

7. **Deploy the Stack:**
   - Click "Deploy the stack"
   - Wait 3-5 minutes for initial build

## Step 4: Verify Deployment

### Check Container Status:
In Portainer → Stacks → `premiummeter`, verify all containers are running:
- ✅ `premiummeter_db` (database)
- ✅ `premiummeter_backend` (API)
- ✅ `premiummeter_frontend` (web UI)

### Access the Application:
- **Frontend**: `http://YOUR_NAS_IP:3000`
- **Backend API**: `http://YOUR_NAS_IP:8000/docs`
- **Health Check**: `http://YOUR_NAS_IP:8000/health`

### Check Logs:
If issues occur, check logs in Portainer:
1. Go to Containers
2. Click container name
3. Click "Logs" tab

## Step 5: Database Initialization

The database schema will be created automatically on first run via Alembic migrations. To verify:

1. Open backend container logs in Portainer
2. Look for migration success messages:
   ```
   INFO  [alembic.runtime.migration] Running upgrade
   ```

## Common Environment Configurations

### For Synology NAS:
```env
VITE_API_URL=http://synology-ip:8000/api
ALLOWED_ORIGINS=http://synology-ip:3000
```

### For QNAP NAS:
```env
VITE_API_URL=http://qnap-ip:8000/api
ALLOWED_ORIGINS=http://qnap-ip:3000
```

### Multiple Access Points:
```env
ALLOWED_ORIGINS=http://192.168.1.100:3000,http://nas.local:3000
```

## Troubleshooting

### Container Won't Start:

1. **Check environment variables** are set correctly
2. **Check logs** in Portainer container view
3. **Verify ports** 3000, 8000, 5432 are not in use

### Frontend Can't Connect to Backend:

1. Verify `VITE_API_URL` includes `/api` path
2. Check `ALLOWED_ORIGINS` matches your frontend URL
3. Ensure backend container is running and healthy

### Database Connection Failed:

1. Check `POSTGRES_PASSWORD` matches in all services
2. Wait for database health check to pass (can take 30s)
3. Verify volume `postgres_data` has correct permissions

### Build Fails:

1. Check GitHub repository is accessible
2. Verify `docker-compose.portainer.yml` exists in repo root
3. Check Dockerfile.prod files exist in backend/ and frontend/ folders

## Auto-Deploy on Git Push (Optional)

To automatically rebuild when you push to GitHub:

1. In Portainer, enable webhook for your stack
2. Copy the webhook URL
3. In GitHub: Settings → Webhooks → Add webhook
4. Paste Portainer webhook URL
5. Set content type: `application/json`
6. Select: "Just the push event"
7. Save

Now every `git push` will trigger redeployment.

## Backup Recommendations

### Database Backup:
```bash
# In Portainer console or NAS terminal
docker exec premiummeter_db pg_dump -U premiummeter premiummeter > backup.sql
```

### Full Stack Backup:
Backup the PostgreSQL volume:
- Portainer → Volumes → `premiummeter_postgres_data` → Export

## Updating the Application

### Manual Update:
1. Push changes to GitHub
2. In Portainer: Stacks → `premiummeter` → "Pull and redeploy"
3. Click "Redeploy" button

### With Webhook (Automatic):
- Just push to GitHub - auto-deploys in ~2-3 minutes

## Security Considerations

1. **Change default passwords** in environment variables
2. **Use strong SECRET_KEY** (minimum 32 characters)
3. **Restrict port access** using firewall rules
4. **Use HTTPS** with reverse proxy (Nginx Proxy Manager, Traefik)
5. **Regular backups** of database volume
6. **Keep Docker images updated** (rebuild monthly)

## Production Optimizations

### Enable HTTPS with Reverse Proxy:
Consider using Nginx Proxy Manager or Traefik:
- Set up SSL certificates (Let's Encrypt)
- Update `VITE_API_URL` to use `https://`
- Update `ALLOWED_ORIGINS` to use `https://`

### Resource Limits:
Add to docker-compose.portainer.yml if needed:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## Support

For issues:
1. Check container logs in Portainer
2. Verify environment variables
3. Check GitHub repository is up to date
4. Review this guide's troubleshooting section
