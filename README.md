# Putty Manufacturing Workflow System

A simple web-based production tracking system for an adhesive / wall putty manufacturer.

## Features

- **Admin Dashboard** – Create orders, assign mixing stations, manage raw material stock, advance order status
- **Packing Hall Screen** – Large, projector-friendly view of orders ready for packing / packed / ready to ship
- **3 Mixing Station Screens** – Each shows the currently assigned order + full recipe with exact kg quantities to weigh
- Automatic stock deduction when mixing is completed
- Low-stock alerts
- Sample products and recipes based on typical cement-based and acrylic putty formulations

## Screens

| Screen              | Path              |
|---------------------|-------------------|
| Admin / Control     | `/`               |
| Packing Hall        | `/packing`        |
| Mixing Station 1    | `/mixing/1`       |
| Mixing Station 2    | `/mixing/2`       |
| Mixing Station 3    | `/mixing/3`       |

## Quick Start (Local)

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open:

- http://127.0.0.1:5000/          → Admin
- http://127.0.0.1:5000/packing   → Packing Hall
- http://127.0.0.1:5000/mixing/1  → Mixer 1 (etc.)

## Deploying

### Option A – Render.com (recommended free Python host)

1. Fork or import this repo on [render.com](https://render.com)
2. Create a new **Web Service**
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Add environment variable if needed (none required for basic use)

### Option B – Cloudflare Tunnel (expose your local machine securely)

```bash
# Install cloudflared, then:
cloudflared tunnel --url http://localhost:5000
```

This gives you a public `*.trycloudflare.com` URL you can point projectors / tablets at.

### Option C – Railway / Fly.io / any Docker host

The app is a standard Flask + SQLite application. No external services required.

## Notes

- SQLite database is created automatically on first run (`putty.db`)
- Change `app.secret_key` before any real production use
- For multi-user / multi-location production use, consider moving to PostgreSQL and adding authentication

## License

MIT – free to use and modify for your factory.
