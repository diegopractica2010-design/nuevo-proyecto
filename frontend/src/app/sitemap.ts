import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "https://yourdomain.com";
  return [
    { url: base, lastModified: new Date(), changeFrequency: "daily", priority: 1 },
    { url: `${base}/baskets`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.7 },
    { url: `${base}/profile`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.5 },
  ];
}
