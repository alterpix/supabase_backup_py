# 📦 Installation Guide

## Prerequisites

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Supabase Account** - [Sign up for Supabase](https://supabase.com)
- **Supabase Credentials**:
  - `SUPABASE_URL` - Your Supabase project URL
  - `SUPABASE_SERVICE_ROLE_KEY` - Service role key (not anon key)

## Step-by-Step Installation

### 1. Download/Clone Repository

```bash
# If using git
git clone https://github.com/alterpix/supabase_backup_py
cd backup_release

# Or download and extract ZIP file
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `supabase` - Supabase Python client
- `python-dotenv` - Environment variable management
- `psycopg2-binary` - PostgreSQL adapter (optional, for direct connection)

### 4. Configure Environment Variables

```bash
# Copy example file
cp env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

Fill in your Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

**Where to find credentials:**
1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** (secret) → `SUPABASE_SERVICE_ROLE_KEY`

⚠️ **Important**: Use `service_role` key, not `anon` key. Service role key has full database access.

### 5. Verify Installation

```bash
# Test connection
python backup_supabase.py --list

# If successful, you should see backup list or "No backups found"
```

## Quick Test

```bash
# Create a test backup
python backup_supabase.py

# List backups
python backup_supabase.py --list
```

## Troubleshooting Installation

### Error: "No module named 'supabase'"

**Solution**: Make sure virtual environment is activated and dependencies are installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Error: "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"

**Solution**: 
1. Check `.env` file exists
2. Verify credentials are correct
3. Make sure no quotes around values in `.env`

### Error: "password authentication failed"

**Solution**: 
- Verify `SUPABASE_SERVICE_ROLE_KEY` is correct
- Make sure you're using `service_role` key, not `anon` key
- Check for extra spaces or newlines in `.env` file

## Next Steps

After installation:
1. ✅ Read [QUICK_START.md](QUICK_START.md) for basic usage
2. ✅ Read [SAFETY_FEATURES.md](SAFETY_FEATURES.md) for safe restore
3. ✅ Set up cron job for automated backups (see `cron_example.txt`)

## Support

If you encounter issues:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Verify all prerequisites are met
3. Check `.env` file configuration

