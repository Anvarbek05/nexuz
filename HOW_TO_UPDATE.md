# Step 6: how to put this version into your project (Windows)

Do part 1 first. Parts 2 to 6 are for the live website on Render. Do them in this order.

## Part 1. Update your computer and test it

1. Close `uvicorn` in the VS Code terminal (press Ctrl+C).
2. Extract the zip. You get a folder named `nexuz-pro`. Open it: you must see `app`, `static`, `tests`,
   `requirements.txt` directly inside.
3. Open your project folder (`D:\nexuz-pro`) in File Explorer.
4. DELETE these three folders from your project: `app`, `static`, `tests`.
   (Do NOT delete `venv`, `.git` or `data`.)
5. COPY into your project, from the extracted folder: `app`, `static`, `tests`, and the files
   `requirements.txt`, `requirements-dev.txt`, `render.yaml`, `README.md`, `HANDOFF.md`, `HOW_TO_UPDATE.md`, `.gitignore`.
6. Check: `D:\nexuz-pro\app\services\payments.py` exists, and there is NO `tests\tests` folder.
7. In the VS Code terminal:
   ```
   venv\Scripts\activate
   pip install -r requirements-dev.txt
   pytest
   ```
   Expect: everything green, `0 failed`. The number is bigger than 75 now (new tests for accounts, limits, payments).
   If something is red, copy the red text and send it to me.
8. Start the site and try it:
   ```
   uvicorn app.main:app --reload
   ```
   Open http://127.0.0.1:8000. Click "Sign in", create an account, use a tool, open "Pricing", "Privacy", "Terms".
   Your accounts on your own computer are in the file `D:\nexuz-pro\data\nexuz.db` (git ignores it).
9. Try the limits: use any tool 5 times without signing in. The 6th time you must see a message that the free
   uses for today are finished. After you sign in you get 25 uses a day.
10. Save to GitHub (Render redeploys by itself):
    ```
    git add .
    git commit -m "Step 6: accounts, limits, legal pages, payments (off)"
    git push
    ```

IMPORTANT: until you finish part 2, the live site REFUSES new accounts (it shows "Creating accounts is not
available yet"). This is on purpose. Render's free disk is erased every time the site sleeps or redeploys, so
accounts saved there would disappear.

## Part 2. A database for the live site (needed for accounts)

Render's own free database is deleted 30 days after you create it (Render docs, checked 14 Nov 2026), so it is
not good for real users. Use a free PostgreSQL from another company. Two common choices are Neon (neon.tech) and
Supabase (supabase.com). Check their current free terms before you choose.

1. Create a free account on the service you chose, and create a PostgreSQL database.
2. Copy the connection string. It starts with `postgresql://`.
3. Open https://dashboard.render.com, open the service `nexuz`, open the tab Environment.
4. Add a variable: key `DATABASE_URL`, value = the connection string. Save. Render restarts the site.
5. Open https://nexuz-vtcb.onrender.com/en/register and create a test account. If it works, the database works.
   Nexuz creates its tables by itself the first time.

Law check (important): Uzbekistan has rules about storing personal data of its citizens (emails count). Ask a
lawyer if a database outside Uzbekistan is allowed for your case. I am not a lawyer.

## Part 3. Other settings on Render (tab Environment)

| Key | What to write |
|---|---|
| `CONTACT_EMAIL` | your public email, shown on the Privacy and Terms pages |
| `ADMIN_TOKEN` | a long secret you invent (30+ random letters and digits). Keep it private. |
| `PROXY_HOPS` | already `3` in render.yaml. Check it below. |

Check PROXY_HOPS (so the "5 uses a day for guests" limit sees your real IP address). In PowerShell:
```
Invoke-RestMethod -Uri https://nexuz-vtcb.onrender.com/api/admin/ip -Headers @{ "X-Admin-Token" = "YOUR_ADMIN_TOKEN" }
```
Look at `client_ip`. Compare it with your real address (search "what is my ip" in Google). If they are different,
change `PROXY_HOPS` to 1, 2 or 4 and test again until it matches.

## Part 4. Google Search Console

1. Open https://search.google.com/search-console and sign in with your Google account.
2. Click "Add property". Choose "URL prefix" (the right box). Write `https://nexuz-vtcb.onrender.com/` and continue.
   (Do not choose "Domain": it needs DNS settings, and you cannot change DNS of onrender.com.)
3. Choose the verification method "HTML tag". Google shows a line like
   `<meta name="google-site-verification" content="ABC123...">`. Copy ONLY the part inside `content="..."`.
4. On Render, tab Environment, add: key `GOOGLE_SITE_VERIFICATION`, value = that copied part. Save and wait until
   Render finishes restarting (1 to 3 minutes).
5. Go back to Search Console and click "Verify".
6. In the left menu click "Sitemaps". Write `sitemap.xml` and click "Submit".
7. Google needs days or weeks to show pages in search. This is normal.
When you buy your own domain later, add it as a new property and change `SITE_URL` on Render.

## Part 5. Give Premium by hand (while payments are off)

For a person who paid you in another way (bank transfer, Telegram). Premium is added after the current end date.
In PowerShell (30 days for person@example.com):
```
Invoke-RestMethod -Method Post -Uri https://nexuz-vtcb.onrender.com/api/admin/premium `
  -Headers @{ "X-Admin-Token" = "YOUR_ADMIN_TOKEN" } -ContentType "application/json" `
  -Body '{"email": "person@example.com", "days": 30}'
```
`days: 0` removes Premium. On your own computer you can also use `python -m app.admin users`,
`python -m app.admin grant person@example.com 30` (this works only with your local database).

## Part 6. Payments with Click and Payme (built, but switched OFF)

What is built: the order table, the "Pay" buttons on the Pricing page, and the server parts that Click and Payme
call. They switch on by themselves when ALL the keys of a provider are in the Render environment.

What is NOT done, and why:
- I could not test it with the real Click or Payme test servers. The code follows their public documents and my
  own tests, but you MUST test every step in their sandbox before real money.
- Payme works only with legal entities (IP, OOO and so on, from Payme's own documents). Click also needs a
  contract. You probably need a registered business first.
- Uzum is NOT built. I could not find its technical documents. Send me them when you have a contract.
- Refunds are by hand. If Payme asks to cancel a paid order, our server answers "cannot cancel".

When you have a contract:
1. Give the provider these addresses (use your real site address):
   - Click: Prepare `https://nexuz-vtcb.onrender.com/api/pay/click/prepare`, Complete `https://nexuz-vtcb.onrender.com/api/pay/click/complete`
   - Payme: `https://nexuz-vtcb.onrender.com/api/pay/payme`
2. Put the keys in Render, tab Environment: Click `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`;
   Payme `PAYME_MERCHANT_ID`, `PAYME_KEY` (and `PAYME_TEST` = `1` while you test in Payme's test mode).
3. Set the price in `PREMIUM_PRICE_SUM` (soums for 30 days).
4. Run all the provider's sandbox tests. Send me any error text and I fix it.
5. The Terms and Privacy pages change by themselves when a provider is on (they start to talk about paying).
   Ask a lawyer to read them before you sell anything.
