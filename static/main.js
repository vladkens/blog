document.addEventListener("DOMContentLoaded", () => {
  const markCurrentLinks = () => {
    const loc = document.location.pathname.replace(/\/$/, "");

    document
      .querySelectorAll(`a[href="${loc}"],a[href="${loc}/"]`)
      .forEach((x) => x.classList.add("current"));
  };

  const addCopyCodeButton = () => {
    document.querySelectorAll("pre").forEach((x) => {
      const el = document.createElement("button");
      el.classList.add("copy-code");
      el.innerHTML = "Copy";
      el.onclick = () => {
        navigator.clipboard.writeText(x.querySelector("code").innerText);
        el.innerHTML = "Copied!";
        setTimeout(() => (el.innerHTML = "Copy"), 2000);
      };
      x.appendChild(el);
    });
  };

  markCurrentLinks();
  addCopyCodeButton();
});
