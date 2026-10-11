from db.mongo_conn import get_collection

def waste_by_reason(donor_id=None):
    pipeline = [
         {
                    '$group': {
                        '_id': '$reason', 
                        'total_kg': {
                            '$sum': '$qty_kg'
                        }, 
                        'logs': {
                            '$sum': 1
                        }
                    }
                }, {
                    '$sort': {
                        'total_kg': -1
                    }
                }, {
                    '$project': {
                        '_id': 0, 
                        'reason': '$_id', 
                        'total_kg': {
                            '$round': [
                                '$total_kg', 2
                            ]
                        }, 
                        'logs': 1
                    }
                }
    ]
    return _run(pipeline, donor_id)

def waste_by_category(donor_id=None):
    pipeline = [
        {
            '$group': {
                '_id': '$category', 
                'total_kg': {
                    '$sum': '$qty_kg'
                }, 
                'logs': {
                    '$sum': 1
                }
            }
        }, {
            '$sort': {
                'total_kg': -1
            }
        }, {
            '$project': {
                '_id': 0, 
                'category': '$_id', 
                'total_kg': {
                    '$round': [
                        '$total_kg', 2
                    ]
                }, 
                'logs': 1
            }
        }
    ]
    return _run(pipeline, donor_id)

def waste_by_month(donor_id=None):
    pipeline = [
        {
            '$group': {
                '_id': {
                    '$dateToString': {
                        'format': '%Y-%m', 
                        'date': '$recorded_at'
                    }
                }, 
                'total_kg': {
                    '$sum': '$qty_kg'
                }, 
                'logs': {
                    '$sum': 1
                }
            }
        }, {
            '$sort': {
                '_id': 1
            }
        }, {
            '$project': {
                '_id': 0, 
                'month': '$_id', 
                'total_kg': {
                    '$round': [
                        '$total_kg', 2
                    ]
                }, 
                'logs': 1
            }
        }
    ]
    return _run(pipeline, donor_id)

def waste_totals_by_donor(donor_id=None):
    pipeline = [
        {
            '$group': {
                '_id': '$donor_id', 
                'total_kg': {
                    '$sum': '$qty_kg'
                }, 
                'logs': {
                    '$sum': 1
                }
            }
        }, {
            '$sort': {
                'total_kg': -1
            }
        }, {
            '$project': {
                '_id': 0, 
                'donor_id': '$_id', 
                'total_kg': {
                    '$round': [
                        '$total_kg', 2
                    ]
                }, 
                'logs': 1
            }
        }
    ]
    return _run(pipeline, donor_id)

def _run(pipeline, donor_id=None):
    if donor_id is not None:
        pipeline.insert(0, {"$match": {"donor_id": donor_id}})
    return list(get_collection("waste_logs").aggregate(pipeline))