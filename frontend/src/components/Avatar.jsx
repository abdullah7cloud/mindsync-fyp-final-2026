import { useEffect, useState } from "react";
import { api } from "../api";

// The student's picture, or their initial in a coloured circle. The picture needs the login, so it is fetched with it and shown from memory.
export default function Avatar({ token, name, version = 0, size = 40, className = "" }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let dead = false, made = null;
    setUrl(null);
    if (token && version > 0) {
      api.myPicture(token).then(({ blob }) => { if (!dead) { made = URL.createObjectURL(blob); setUrl(made); } }).catch(() => {});
    }
    return () => { dead = true; if (made) URL.revokeObjectURL(made); };
  }, [token, version]);
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";
  const style = { width: size, height: size, fontSize: Math.round(size * 0.42) };
  return url
    ? <img className={`p28-avatar ${className}`} style={style} src={url} alt="" />
    : <span className={`p28-avatar p28-avatar-initial ${className}`} style={style} aria-hidden="true">{initial}</span>;
}
