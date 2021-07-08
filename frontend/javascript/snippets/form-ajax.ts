interface IHTMLModalTriggerElement extends HTMLElement { Modal: any | null; }

const confirmForm = (form: HTMLElement) => {
  const confirmMessage = form.dataset.confirm;
  if (!confirmMessage) {
    return true;
  }
  const confirmed = window.confirm(confirmMessage);
  if (!confirmed) {
    return false;
  }
  return true;
};

const submitFormsAjax = () => {
  const ajaxForms = document.querySelectorAll("form.ajaxified");
  (Array.from(ajaxForms) as HTMLFormElement[]).forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();

      if (!confirmForm(form)) {
        return false;
      }

      const method = form.getAttribute("method") || "post";
      const url = form.getAttribute("action") || "";
      const formData = new FormData(form);
      const data = Array.from(formData)
        .map((pair) => pair.map((x) => encodeURIComponent(x.toString())).join("="))
        .join("&");

      const request = new XMLHttpRequest();
      request.open(method, url, true);
      request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
      request.setRequestHeader("X-Requested-With", "XMLHttpRequest");
      request.onload = () => {

        if (form.dataset.modal) {
          const modalTrigger = document.getElementById(form.dataset.modal) as IHTMLModalTriggerElement;
          if (modalTrigger) {
            modalTrigger.Modal.hide();
          }
        }

        const responseData = request.responseText;
        if (responseData[0] === "/") {
          // starts with URL, redirect
          window.location.href = responseData;
          if (responseData.indexOf('#') !== -1) {
            window.location.reload(true);
          }
          return;
        }
        const parent = form.closest(".ajax-parent");
        if (parent) {
          if (responseData[0] === "{") {
            const data = JSON.parse(responseData)
            if (data.errors) {
              parent.outerHTML = `<div class="alert alert-danger">${data.errors}</div>`;
            }
          } else {
            parent.outerHTML = responseData;
          }
        } else {
          form.outerHTML = responseData
        }
      };
      request.send(data);

      Array.from(form.querySelectorAll("button, input")).forEach((el) => {
        if (el.getAttribute('type') === 'submit') {
          el.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>${el.innerHTML}`
        }
        el.setAttribute("disabled", "");
      });
    });
  });
};

submitFormsAjax();

export default {
  submitFormsAjax,
};
