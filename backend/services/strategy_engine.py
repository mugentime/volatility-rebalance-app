def _log_transaction(self, tx_type, asset, amount, status='completed', extra_info=None):
    """Log transaction to database"""
    try:
        transaction = Transaction(
            transaction_type=tx_type,
            asset=asset,
            amount=str(amount),  # Store as string
            status=status,
            timestamp=datetime.utcnow(),
            extra_data=extra_info  # Changed from metadata to extra_data
        )
        db.session.add(transaction)
        db.session.commit()
    except Exception as e:
        logging.error(f"Failed to log transaction: {e}")
