const api = new URL(process.env.CONVX_API_URL || "http://127.0.0.1:8000");
if (
  !["http:", "https:"].includes(api.protocol) ||
  api.username ||
  api.password ||
  api.pathname !== "/" ||
  api.search ||
  api.hash
) {
  throw new Error(
    "CONVX_API_URL must be a trusted HTTP(S) origin without credentials or a path",
  );
}

export default {
  agentRules: false,
  distDir: process.env.CONVX_LOCAL_LAUNCHER === "1" ? ".next-local" : ".next",
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${api.origin}/api/v1/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};
