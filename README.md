# NDA_GBB_Stats

## Google sign-in setup

The app uses Streamlit's OpenID Connect sign-in with Google. Only verified
Google email addresses listed in the `[admin]` allowlist can access admin pages.
All other visitors can use guest access.

1. In Google Cloud Console, configure the OAuth consent screen and create an
   OAuth client ID for a **Web application**.
2. Add the exact callback URL to the OAuth client's authorized redirect URIs:
   `http://localhost:8501/oauth2callback` for local development and
   `https://YOUR-DEPLOYED-APP-URL/oauth2callback` for the deployed app.
3. Create `.streamlit/secrets.toml` locally and add the deployed values to the
   hosting provider's secrets configuration:

   ```toml
   [auth]
   redirect_uri = "http://localhost:8501/oauth2callback"
   cookie_secret = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
   client_id = "YOUR_GOOGLE_CLIENT_ID"
   client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

   [admin]
   emails = []
   ```

   Use the deployed callback URL in the deployed secrets. Keep
      `.streamlit/secrets.toml` private and do not commit it. Add each authorized
      Google account's email address to the `emails` list; an empty list grants no
      admin access.
4. If the Google OAuth consent screen is in testing mode, add each intended
   admin as a test user there as well as to the app's `[admin]` email list.

Create and activate this app's Python 3.13 environment in PowerShell, then
install the requirements. The NumPy and Pillow pins use versions with Python
3.13 Windows wheels; the existing pins did not provide them.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run Home.py
```
