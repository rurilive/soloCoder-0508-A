export const checkPathActive = (items, pathname) => {
  return items.some(item => {
    if (item.path === pathname) return true
    if (item.children) {
      return checkPathActive(item.children, pathname)
    }
    return false
  })
}

export const getBreadcrumbPath = (items, pathname, currentPath = []) => {
  for (const item of items) {
    const newPath = [...currentPath, { label: item.label, path: item.path }]
    if (item.path === pathname) {
      return newPath
    }
    if (item.children) {
      const found = getBreadcrumbPath(item.children, pathname, newPath)
      if (found) return found
    }
  }
  return null
}
