# Peer Evaluation Django Project

This is a Django-based peer evaluation system.  
Follow the instructions below to set up, configure, and deploy the project.

---

## 🎬 Project Preview

You can watch a demo of the project here:

[Watch the demo](https://youtu.be/6OE4hhoTwdg)

### 1. **Clone the Repository**

```bash
git clone https://github.com/yourusername/peer_eval.git
cd peer_eval
```

### 2. **Create and Activate a Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 4. **Configure Database and Settings**

- By default, the project uses PostgreSQL for local development.
- **Edit `peer_eval/settings.py`**:
  - Update the `DATABASES` section with your local PostgreSQL credentials:
    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'peer_eval_db',
            'USER': 'your_db_user',
            'PASSWORD': 'your_db_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
    ```
  - Make sure `ALLOWED_HOSTS` is set to:
    ```python
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    ```
  - For local file storage, ensure:
    ```python
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    ```

### 5. **Apply Migrations**

```bash
python manage.py migrate
```

### 6. **Create a Superuser**

```bash
python manage.py createsuperuser
```
- Enter your own username, email, and password (your password will be private).

### 7. **Run the Development Server**

```bash
python manage.py runserver
```
- Visit [http://localhost:8000/admin/](http://localhost:8000/admin/) and log in with your superuser credentials.

---

## 👩‍🏫 Adding a Teacher User for Testing

1. **Log in to the Django admin at `/admin/` using your superuser account.**
2. **Navigate to the "Users" section.**
3. **Click "Add user".**
4. **Fill in the username, password, and email.**
5. **After saving, edit the user and assign them to the "teacher" group or set the appropriate permissions/roles as needed for your app.**

---

## 🌐 Deployment on Render

### 1. **Prepare for Deployment**

- Make sure you have a `render.yaml` file in your repo (already provided).
- Remove any sensitive information (like secret keys) from `settings.py` and use environment variables instead.

### 2. **Environment Variables**

On Render, set the following environment variables in the dashboard:

```
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com
DATABASE_URL=your-render-postgres-url
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-s3-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### 3. **Update `settings.py` for Production**

- Use `django-environ` to read environment variables:
    ```python
    import environ
    env = environ.Env()
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

    SECRET_KEY = env('SECRET_KEY')
    DEBUG = env.bool('DEBUG', default=False)
    ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
    DATABASES = {
        'default': env.db('DATABASE_URL')
    }
    # S3 storage settings...
    ```

### 4. **Deploy**

- Push your code to GitHub.
- Connect your repo to Render and deploy.
- On Render, run:
    ```bash
    python manage.py migrate
    ```
- To create a superuser on Render, set these environment variables:
    ```
    DJANGO_SUPERUSER_USERNAME=youradmin
    DJANGO_SUPERUSER_EMAIL=your@email.com
    DJANGO_SUPERUSER_PASSWORD=yourpassword
    ```
    Then run:
    ```bash
    python manage.py createsuperuser --noinput
    ```
    Remove these variables after the superuser is created.

---

## 📝 Notes

- **Never commit your `.env` file or secrets to git.**
- **Always rotate secrets if they are accidentally exposed.**
- For local testing, you can use SQLite by setting:
    ```
    DATABASE_URL=sqlite:///db.sqlite3
    ```
    in your `.env` and updating `settings.py` to use `django-environ`.

---

## 📄 Sample `render.yaml`

```yaml
services:
  - type: web
    name: peer-eval
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn peer_eval.wsgi:application
    envVars:
      - key: DJANGO_SETTINGS_MODULE
        value: peer_eval.settings
```

---

## 🤝 Contributing

Feel free to fork and submit pull requests!

---

## 📧 Support

For issues, open a GitHub issue or contact the maintainer.

---
