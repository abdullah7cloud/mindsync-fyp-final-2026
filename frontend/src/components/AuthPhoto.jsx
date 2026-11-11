import Photo from "./Photo";

// A friendly photo beside the log-in and sign-up forms (never behind them). Hidden on small screens.
export default function AuthPhoto() {
  return (
    <aside className="auth-photo" aria-label="Welcome">
      <Photo
        name="friends"
        className="auth-photo-img"
        sizes="55vw"
        focus="50% 40%"
        alt="Three friends laughing at a café table while they work on their laptops"
      />
      <div className="auth-photo-shade" aria-hidden="true" />
      <div className="auth-photo-copy">
        <p className="auth-photo-title">Study Smarter. Feel Better.</p>
        <p>Plan your studies, stay organized, and feel more in control of your day.</p>
      </div>
    </aside>
  );
}
