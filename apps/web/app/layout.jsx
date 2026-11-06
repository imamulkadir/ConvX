import "./globals.css";

export const metadata = {
  title: "DOCX & PDF to HTM Converter | ConvX",
  description:
    "Convert Word and PDF documents into high-fidelity HTM with optional SEC EDGAR compliance.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
