// Icons from: https://www.untitledui.com/icon/copy-06 https://www.untitledui.com/icon/check

const CopyIcon = `
<svg
    width="100%"
    height="100%"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M7.5 3H14.6C16.8402 3 17.9603 3 18.816 3.43597C19.5686 3.81947 20.1805 4.43139 20.564 5.18404C21 6.03969 21 7.15979 21 9.4V16.5M6.2 21H14.3C15.4201 21 15.9802 21 16.408 20.782C16.7843 20.5903 17.0903 20.2843 17.282 19.908C17.5 19.4802 17.5 18.9201 17.5 17.8V9.7C17.5 8.57989 17.5 8.01984 17.282 7.59202C17.0903 7.21569 16.7843 6.90973 16.408 6.71799C15.9802 6.5 15.4201 6.5 14.3 6.5H6.2C5.0799 6.5 4.51984 6.5 4.09202 6.71799C3.71569 6.90973 3.40973 7.21569 3.21799 7.59202C3 8.01984 3 8.57989 3 9.7V17.8C3 18.9201 3 19.4802 3.21799 19.908C3.40973 20.2843 3.71569 20.5903 4.09202 20.782C4.51984 21 5.0799 21 6.2 21Z"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
</svg>
`.trim();

const CheckIcon = `
<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
 <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
`.trim();

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
      el.innerHTML = CopyIcon;
      el.onclick = () => {
        navigator.clipboard.writeText(x.querySelector("code").innerText);
        el.innerHTML = CheckIcon;
        el.classList.add("copied");
        setTimeout(() => {
          el.innerHTML = CopyIcon;
          el.classList.remove("copied");
        }, 2000);
      };
      x.appendChild(el);
    });
  };

  markCurrentLinks();
  addCopyCodeButton();
});
