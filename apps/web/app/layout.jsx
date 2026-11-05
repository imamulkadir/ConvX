import "./globals.css";

export const metadata = {
  title: "ConvX · Filing workspace",
  description: "Document conversion, validation and visual review.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
