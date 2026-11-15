// Delay single-click changes so a double-click can open the original node.
function createNodeActivation(singleClick, doubleClick, delay = 500,
                              schedule = setTimeout, cancelScheduled = clearTimeout) {
  let pending = null;
  function cancel() {
    if (pending !== null) {
      cancelScheduled(pending);
      pending = null;
    }
  }
  return {
    cancel,
    click(node) {
      cancel();
      if (node.children.length === 0) return;
      pending = schedule(() => {
        pending = null;
        singleClick(node);
      }, delay);
    },
    doubleClick(node) {
      cancel();
      doubleClick(node);
    },
  };
}
