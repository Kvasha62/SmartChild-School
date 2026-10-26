document.querySelectorAll("[data-lesson-tabs]").forEach((group) => {
      const buttons = Array.from(
        group.querySelectorAll("[data-tab-button]")
      );
      const panels = Array.from(
        group.querySelectorAll("[data-tab-panel]")
      );

      function activate(index, moveFocus = false) {
        buttons.forEach((button, i) => {
          const active = i === index;
          button.setAttribute("aria-selected", String(active));
          button.tabIndex = active ? 0 : -1;
          panels[i].hidden = !active;
        });

        if (moveFocus) {
          buttons[index].focus();
        }
      }

      buttons.forEach((button, index) => {
        button.addEventListener("click", () => activate(index));

        button.addEventListener("keydown", (event) => {
          let next = index;

          if (event.key === "ArrowRight") {
            next = (index + 1) % buttons.length;
          } else if (event.key === "ArrowLeft") {
            next = (index - 1 + buttons.length) % buttons.length;
          } else if (event.key === "Home") {
            next = 0;
          } else if (event.key === "End") {
            next = buttons.length - 1;
          } else {
            return;
          }

          event.preventDefault();
          activate(next, true);
        });
      });
    });
