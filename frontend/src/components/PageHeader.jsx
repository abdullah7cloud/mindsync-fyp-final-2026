import Photo from "./Photo";

// The top of every page. It answers three questions in plain words: what is this page for (title + subtitle),
// what can I do here (subtitle), and what should I click first ("start" line).
// Pages with a photo show it as a banner: the picture fills the top of the page and the words sit on a soft dark
// gradient so they stay easy to read. Forms, lists and charts are never placed on top of a photo.
export default function PageHeader({ title, subtitle, start, image, children }) {
  const text = (
    <>
      <h1>{title}</h1>
      {subtitle && <p className="page-subtitle">{subtitle}</p>}
      {start && <p className="start-here"><span>Start here</span>{start}</p>}
      {children && <div className="page-header-actions">{children}</div>}
    </>
  );
  if (image) {
    return (
      <header className={`page-header page-banner banner-${image.side === "right" ? "right" : "left"}`}>
        <Photo
          name={image.name}
          alt={image.alt}
          focus={image.focus}
          className="banner-img"
          sizes="(max-width: 1100px) 100vw, 1000px"
        />
        <div className="banner-shade" aria-hidden="true" />
        <div className="page-header-text banner-text">{text}</div>
      </header>
    );
  }
  return (
    <header className="page-header">
      <div className="page-header-text">{text}</div>
    </header>
  );
}
