export function initials(name: string) {
  return name
    .replace(/^Dr\s+/, '')
    .split(/\s+/)
    .filter((part) => /^[A-Z]/.test(part))
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
}
