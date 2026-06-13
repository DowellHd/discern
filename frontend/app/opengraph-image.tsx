import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Discern — Document Intelligence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0f172a",
          fontFamily: "system-ui, -apple-system, sans-serif",
          gap: 0,
        }}
      >
        {/* Logomark */}
        <div
          style={{
            width: 88,
            height: 88,
            borderRadius: 22,
            background: "linear-gradient(135deg, #6366f1 0%, #4338ca 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 36,
            boxShadow: "0 20px 60px rgb(99 102 241 / 0.4)",
          }}
        >
          <span style={{ color: "white", fontSize: 46, fontWeight: 700, lineHeight: 1 }}>D</span>
        </div>

        <h1
          style={{
            color: "#ffffff",
            fontSize: 60,
            fontWeight: 700,
            margin: 0,
            letterSpacing: "-1.5px",
            lineHeight: 1,
          }}
        >
          Discern
        </h1>

        <p
          style={{
            color: "#94a3b8",
            fontSize: 26,
            margin: "16px 0 0",
            fontWeight: 400,
            letterSpacing: "-0.3px",
          }}
        >
          Document Intelligence
        </p>

        <p
          style={{
            color: "#475569",
            fontSize: 18,
            margin: "20px 0 0",
            fontWeight: 400,
          }}
        >
          Extract structured data from paper church records
        </p>
      </div>
    ),
    { ...size },
  );
}
