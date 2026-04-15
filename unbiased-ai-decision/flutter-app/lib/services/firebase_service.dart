import 'package:cloud_firestore/cloud_firestore.dart';

import 'api_service.dart';

class FirebaseService {
  FirebaseService._();

  static final FirebaseService instance = FirebaseService._();

  final FirebaseFirestore firestore = FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> get audits =>
      firestore.collection('audits');

  Map<String, dynamic> localSampleAudit() {
    return {
      'audit_id': 'sample_hiring_audit',
      'user_id': 'guest-demo',
      'model_name': 'Resume Screening Model v1.2',
      'dataset_name': 'TechCorp Hiring Data 2022-2023 (n=4,821)',
      'bias_score': 73.0,
      'fairness_metrics': {
        'demographic_parity': 0.31,
        'equalized_odds': 0.28,
        'individual_fairness': 0.64,
        'calibration_error': 0.18,
        'disparate_impact': 0.69,
      },
      'shap_values': const [
        {'feature': 'gender_proxy', 'value': 0.412},
        {'feature': 'zip_code', 'value': 0.307},
        {'feature': 'university_tier', 'value': 0.266},
      ],
      'shap_top3': const ['gender_proxy', 'zip_code', 'university_tier'],
      'causal_graph_json': {
        'nodes': const [
          {'id': 'gender_proxy'},
          {'id': 'zip_code'},
          {'id': 'university_tier'},
          {'id': 'hired'},
        ],
        'edges': const [
          {'source': 'gender_proxy', 'target': 'zip_code', 'weight': 0.33},
          {'source': 'zip_code', 'target': 'hired', 'weight': 0.28},
        ],
      },
      'demographic_parity': 0.31,
      'equalized_odds': 0.28,
      'individual_fairness': 0.64,
      'calibration_error': 0.18,
      'gemini_explanation':
          'The model shows severe gender bias via proxy features, with women 31% less likely to be shortlisted for the same qualifications. This perpetuates workplace inequality and directly undermines SDG 10.3. The organization should remove proxy-heavy inputs such as zip code and retrain on more balanced data.',
      'sdg_tag': 'SDG 10.3',
      'status': 'sample',
      'created_at': DateTime.now().toUtc().toIso8601String(),
    };
  }

  Future<Map<String, dynamic>?> fetchSampleAudit() async {
    try {
      final snapshot = await audits.doc('sample_hiring_audit').get();
      if (snapshot.exists) {
        return _withId(snapshot.data() ?? <String, dynamic>{}, snapshot.id);
      }
    } catch (_) {}

    try {
      return await ApiService.instance.fetchAudit('sample_hiring_audit');
    } catch (_) {
      return localSampleAudit();
    }
  }

  Future<Map<String, dynamic>?> fetchAuditById(String auditId) async {
    try {
      final snapshot = await audits.doc(auditId).get();
      if (snapshot.exists) {
        return _withId(snapshot.data() ?? <String, dynamic>{}, snapshot.id);
      }
    } catch (_) {}

    try {
      return await ApiService.instance.fetchAudit(auditId);
    } catch (_) {
      if (auditId == 'sample_hiring_audit') {
        return localSampleAudit();
      }
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> fetchRecentAudits(
    String userId, {
    int limit = 5,
  }) async {
    try {
      final query = await audits
          .where('user_id', isEqualTo: userId)
          .orderBy('created_at', descending: true)
          .limit(limit)
          .get();
      return query.docs.map((doc) => _withId(doc.data(), doc.id)).toList();
    } catch (_) {
      final history = await ApiService.instance.fetchAuditHistory(userId);
      return history.take(limit).toList(growable: false);
    }
  }

  Stream<List<Map<String, dynamic>>> streamAuditHistory(
    String userId, {
    int limit = 20,
  }) {
    return (() async* {
      try {
        await for (final snapshot in audits
            .where('user_id', isEqualTo: userId)
            .orderBy('created_at', descending: true)
            .limit(limit)
            .snapshots()) {
          yield snapshot.docs
              .map((doc) => _withId(doc.data(), doc.id))
              .toList(growable: false);
        }
      } catch (_) {
        yield await fetchRecentAudits(userId, limit: limit);
      }
    })();
  }

  Future<Map<String, dynamic>> computeDashboardSummary(
    String userId, {
    bool includeSample = false,
  }) async {
    final recentAudits = await fetchRecentAudits(userId, limit: 25);
    final items = <Map<String, dynamic>>[...recentAudits];
    if (includeSample && items.isEmpty) {
      items.add((await fetchSampleAudit()) ?? localSampleAudit());
    }

    final biasScores = items
        .map((audit) => (audit['bias_score'] as num?)?.toDouble() ?? 0)
        .toList(growable: false);
    final avgBias = biasScores.isEmpty
        ? 0.0
        : biasScores.reduce((left, right) => left + right) / biasScores.length;

    return {
      'auditsRun': items.length,
      'avgBiasScore': avgBias,
      'sdgAlignment': 'SDG 10.3',
      'recentAudits': items.take(5).toList(growable: false),
    };
  }

  Map<String, dynamic> _withId(Map<String, dynamic> data, String id) {
    return {
      'audit_id': id,
      ...data,
    };
  }
}
