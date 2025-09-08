import fetch from "node-fetch";

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const { cookie } = req.body;
  if (!cookie) {
    return res.status(400).json({ error: "Missing Roblox cookie" });
  }

  // Fixed birthdate June 5, 2015
  const birthdate = { birthMonth: 6, birthDay: 5, birthYear: 2015 };

  try {
    // First request → get CSRF
    let r = await fetch("https://accountinformation.roblox.com/v1/birthdate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cookie": `.ROBLOSECURITY=${cookie}`
      },
      body: JSON.stringify(birthdate)
    });

    const csrf = r.headers.get("x-csrf-token");
    if (!csrf) return res.status(400).json({ error: "Failed to get CSRF token" });

    // Second request with CSRF
    r = await fetch("https://accountinformation.roblox.com/v1/birthdate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cookie": `.ROBLOSECURITY=${cookie}`,
        "X-CSRF-TOKEN": csrf
      },
      body: JSON.stringify(birthdate)
    });

    const text = await r.text();
    res.status(r.status).json({ status: r.status, response: text });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
