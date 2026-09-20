// A response may update the screen only while it is the newest request
// for the currently selected session.
export function createLatestRequestGuard() {
  let selection = null
  let version = 0

  return {
    select(value) {
      selection = value
      version += 1
    },
    current() {
      return selection
    },
    invalidate() {
      version += 1
    },
    begin(value) {
      const requestVersion = ++version
      return () => selection === value && version === requestVersion
    },
  }
}
