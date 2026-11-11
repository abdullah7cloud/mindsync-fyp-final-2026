import { Link } from "react-router-dom";
import BrandMark from "../components/BrandMark";
import Icon from "../components/Icon";
import Photo from "../components/Photo";
import { useAuth } from "../context/AuthContext";
import "./landing.css";

// The welcome page. Written for someone who has never used a study app: one big photo, one headline, one sentence
// about what MindSync does, one big button, four benefits and three steps. Nothing technical is shown here (that
// lives on the "How It Works" page). The photographs are real people photographed by others (credits in the
// footer and in docs/IMAGE_CREDITS.md); they are for illustration and do not mean anyone endorses MindSync.
const BENEFITS = [
  ["tasks", "See your whole week at a glance", "Your dashboard shows what is done, what is left and what is due soon."],
  ["planner", "Get a study plan in one click", "Tell MindSync what you want to learn and when it is due. You get a simple roadmap and tasks with times."],
  ["leaf", "Plans that fit how you feel", "Tired or stressed? Say so, and the plan gives you a gentler load."],
  ["analytics", "Quiz yourself on your own notes", "Upload a document and take a quiz made from what is really in it."],
];

const STEPS = [
  ["Make a study plan", "Write the subject, the topic and your deadline. Say how you feel today."],
  ["Follow your tasks", "Tick each task off on your dashboard when you finish it."],
  ["Keep your notes close", "Write notes and keep your documents in My Notebook, then make a quiz when you are ready."],
];

const FEEL = [
  "A clear list of tasks, so you never stare at a blank page",
  "Study times that fit before your deadline",
  "A lighter plan when you are tired or stressed",
];

const FAQ = [
  ["Do I need an account?", "Yes. A free account keeps your plans, tasks, notes and documents safe, so they are still there when you log in again."],
  ["Does MindSync use AI?", "It can. When an AI service is switched on and you are online, it can help write your study plan and make quizzes from your documents. The text you send for that goes to that AI service. When AI is off or you are offline, MindSync still makes your study plan with its own built-in rules. Quizzes need the AI."],
  ["Is this medical advice?", "No. MindSync is a study helper. It cannot diagnose anything or tell you how you really feel. If you feel unwell or overwhelmed, please talk to someone you trust, your university's student support or a doctor."],
];

export default function LandingPage() {
  const { token } = useAuth();
  const startLabel = token ? "Open MindSync" : "Get Started";

  return (
    <div className="lp">
      <header className="lp-hero">
        <Photo
          name="hero"
          priority
          className="lp-hero-img"
          sizes="100vw"
          alt="Five university friends walking together down a sunny street, talking and laughing"
        />
        <div className="lp-hero-shade" aria-hidden="true" />

        <nav className="lp-nav" aria-label="Main">
          <Link to="/" className="lp-brand">
            <BrandMark />
            <span>MindSync</span>
          </Link>
          <div className="lp-nav-links">
            <a href="#how" className="lp-hide-small">How it works</a>
            {token ? (
              <Link to="/dashboard" className="lp-btn lp-btn-sm lp-btn-light">Open MindSync</Link>
            ) : (
              <>
                <Link to="/login" className="lp-link">Log in</Link>
                <Link to="/register" className="lp-btn lp-btn-sm lp-btn-light">Create free account</Link>
              </>
            )}
          </div>
        </nav>

        <div className="lp-hero-copy">
          <p className="lp-eyebrow">A friendly study planner for students</p>
          <h1>Study Smarter. <span className="lp-accent">Feel Better.</span></h1>
          <p className="lp-lead">
            Plan your studies, stay organized, and feel more in control of your day.
          </p>
          <div className="lp-cta">
            <Link to={token ? "/dashboard" : "/register"} className="lp-btn lp-btn-lg lp-btn-light">{startLabel}</Link>
            {!token && <Link to="/login" className="lp-btn lp-btn-lg lp-btn-outline">I already have an account</Link>}
          </div>
          <ul className="lp-trust" aria-label="Good to know">
            <li><Icon name="check" size={16} /> Free to try</li>
            <li><Icon name="check" size={16} /> Your data stays in your account</li>
            <li><Icon name="check" size={16} /> Plans work even without AI</li>
          </ul>
        </div>
      </header>

      <main>
        <section className="lp-section lp-benefits-wrap" aria-labelledby="why-title">
          <h2 id="why-title" className="lp-sr">How MindSync helps</h2>
          <div className="lp-benefits">
            {BENEFITS.map(([icon, t, d]) => (
              <article className="lp-benefit" key={t}>
                <span className="lp-benefit-icon"><Icon name={icon} size={22} /></span>
                <h3>{t}</h3>
                <p>{d}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="lp-section lp-how" id="how" aria-labelledby="how-title">
          <div className="lp-how-photo">
            <Photo
              name="friends"
              className="lp-photo"
              sizes="(max-width: 900px) 100vw, 520px"
              alt="Three friends laughing at a café table while they work on their laptops"
            />
          </div>
          <div className="lp-how-copy">
            <p className="lp-kicker">Simple from the first minute</p>
            <h2 id="how-title">It only takes three steps</h2>
            <ol className="lp-steps">
              {STEPS.map(([t, d], i) => (
                <li key={t}>
                  <span className="lp-step-n" aria-hidden="true">{i + 1}</span>
                  <div>
                    <h3>{t}</h3>
                    <p>{d}</p>
                  </div>
                </li>
              ))}
            </ol>
            <Link to={token ? "/dashboard" : "/register"} className="lp-btn">{token ? "Open MindSync" : "Create free account"}</Link>
          </div>
        </section>

        <section className="lp-band" aria-labelledby="band-title">
          <Photo
            name="wellbeing"
            className="lp-band-img"
            sizes="100vw"
            focus="78% 24%"
            alt="A smiling student relaxing on a sofa with her laptop and laughing at something she has read"
          />
          <div className="lp-band-shade" aria-hidden="true" />
          <div className="lp-band-copy">
            <h2 id="band-title">Some days you have lots of energy. Some days you don’t.</h2>
            <p>Tell MindSync how you feel, and your plan stays realistic, so you can keep going without burning out.</p>
            <Link to={token ? "/planner" : "/register"} className="lp-btn lp-btn-light">{token ? "Make a study plan" : "Get started"}</Link>
          </div>
        </section>

        <section className="lp-section lp-feel" aria-labelledby="feel-title">
          <div className="lp-feel-copy">
            <p className="lp-kicker">Feel more in control</p>
            <h2 id="feel-title">A calmer way to get your work done</h2>
            <ul className="lp-checks">
              {FEEL.map((t) => (
                <li key={t}><span aria-hidden="true"><Icon name="check" size={16} /></span>{t}</li>
              ))}
            </ul>
          </div>
          <div className="lp-feel-photo">
            <Photo
              name="grass"
              className="lp-photo"
              sizes="(max-width: 900px) 100vw, 520px"
              alt="Two friends laughing together on the grass with open books"
            />
          </div>
        </section>

        <section className="lp-section" id="faq" aria-labelledby="faq-title">
          <div className="lp-head">
            <h2 id="faq-title">Questions you may have</h2>
          </div>
          <div className="lp-faq">
            {FAQ.map(([q, a]) => (
              <details key={q}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="lp-final">
          <h2>Ready to plan your first study task?</h2>
          <p>It takes about a minute to start. Create a free account and make your first plan.</p>
          <div className="lp-cta" style={{ justifyContent: "center" }}>
            <Link to={token ? "/dashboard" : "/register"} className="lp-btn lp-btn-lg lp-btn-light">{startLabel}</Link>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <span>MindSync · a university final-year project · Study help only, not medical advice.</span>
        <span>
          Photos from Unsplash (free to use): Eliott Reyna, Brooke Cagle, Meredith Spencer,
          Zoshua Colah and Good Faces. The people shown are not MindSync users and do not endorse it.
          Full credits are in the project files.
        </span>
      </footer>
    </div>
  );
}
