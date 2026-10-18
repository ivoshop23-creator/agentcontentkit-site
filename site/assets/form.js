// Email capture: <form class="form" data-source="guide" data-download="/10-ai-prompts-for-listings.pdf">
(function () {
  var utm = (location.search.match(/utm_[a-z]+=[^&]+/g) || []).join('&');
  document.querySelectorAll('form.form').forEach(function (form) {
    var msg = form.parentNode.querySelector('.form-msg');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button'), email = form.email.value.trim();
      msg.textContent = ''; msg.className = 'form-msg';
      if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(email)) {
        msg.textContent = 'Please enter a valid email.'; msg.className = 'form-msg err'; return;
      }
      btn.disabled = true;
      fetch('/api/subscribe', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email: email, source: form.dataset.source, company: form.company.value,
                              referrer: document.referrer, utm: utm})
      }).then(function (r) { return r.json().then(function (j) { return {ok: r.ok && j.ok, j: j}; }); })
        .then(function (res) {
          if (!res.ok) throw new Error(res.j.error || 'Something went wrong. Please try again.');
          var done = document.getElementById(form.dataset.done);
          form.hidden = true; if (done) done.hidden = false;
          if (form.dataset.download) location.href = form.dataset.download;
        })
        .catch(function (err) {
          btn.disabled = false;
          msg.textContent = err.message.indexOf('fetch') > -1 ? 'Connection problem. Please try again.' : err.message;
          msg.className = 'form-msg err';
        });
    });
  });
})();
