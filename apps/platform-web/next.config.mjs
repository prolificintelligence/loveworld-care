/** @type {import('next').NextConfig} */
const config = {
  poweredByHeader: false,
  async rewrites() {
    const origin = process.env.LWH_API_ORIGIN;
    if (!origin) throw new Error("LWH_API_ORIGIN must identify the authoritative platform API");
    return [{ source: "/v1/:path*", destination: `${origin}/v1/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "no-referrer" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
    ] }];
  },
};
export default config;
