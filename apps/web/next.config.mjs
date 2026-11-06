const devPort = process.env.CONVX_DEV_PORT || "default";
if (!/^(?:default|[0-9]{4,5})$/.test(devPort))
  throw new Error("Invalid development port directory");
export default {
  agentRules: false,
  distDir:
    process.env.CONVX_LOCAL_LAUNCHER === "1"
      ? `.next-local-${devPort}`
      : ".next",
  poweredByHeader: false,
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
