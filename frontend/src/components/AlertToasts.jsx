function AlertToasts({ alerts }) {
  return (
    <div className="alerts-container" aria-live="polite" aria-atomic="true">
      {alerts.map((alert) => (
        <div key={alert.id} className={`alert-toast alert-${alert.type}`}>
          {alert.message}
        </div>
      ))}
    </div>
  )
}

export default AlertToasts
