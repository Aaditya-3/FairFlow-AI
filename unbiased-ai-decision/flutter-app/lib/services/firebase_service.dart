import 'package:cloud_firestore/cloud_firestore.dart';

import 'api_service.dart';

class FirebaseService {
  FirebaseService._();

  static final FirebaseService instance = FirebaseService._();

  final FirebaseFirestore firestore = FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> get audits =>
      firestore.collection('audits');

  String createAuditId() => audits.doc().id;

  Future<Map<String, dynamic>> fetchSampleAudit() async {
    final snapshot = await audits.doc('sample_hiring_audit').get();
    if (!snapshot.exists) {
      try {
        return await ApiService.instance.fetchAudit('sample_hiring_audit');
      } catch (_) {
        throw Exception('Firestore sample_hiring_audit is not seeded.');
      }
    }
    return _withId(snapshot.data() ?? <String, dynamic>{}, snapshot.id);
  }

  Future<Map<String, dynamic>?> fetchAuditById(String auditId) async {
    final snapshot = await audits.doc(auditId).get();
    if (snapshot.exists) {
      return _withId(snapshot.data() ?? <String, dynamic>{}, snapshot.id);
    }
    return ApiService.instance.fetchAudit(auditId);
  }

  Future<List<Map<String, dynamic>>> fetchRecentAudits(
    String userId, {
    int limit = 5,
  }) async {
    final query = await audits
        .where('user_id', isEqualTo: userId)
        .orderBy('created_at', descending: true)
        .limit(limit)
        .get();
    return query.docs.map((doc) => _withId(doc.data(), doc.id)).toList();
  }

  Stream<Map<String, dynamic>?> streamAudit(String auditId) {
    return audits.doc(auditId).snapshots().map((snapshot) {
      if (!snapshot.exists) {
        return null;
      }
      return _withId(snapshot.data() ?? <String, dynamic>{}, snapshot.id);
    });
  }

  Stream<List<Map<String, dynamic>>> streamAuditHistory(
    String userId, {
    int limit = 20,
  }) {
    return audits
        .where('user_id', isEqualTo: userId)
        .orderBy('created_at', descending: true)
        .limit(limit)
        .snapshots()
        .map(
          (snapshot) => snapshot.docs
              .map((doc) => _withId(doc.data(), doc.id))
              .toList(growable: false),
        );
  }

  Future<Map<String, dynamic>> computeDashboardSummary(
    String userId, {
    bool includeSample = false,
  }) async {
    final recentAudits = await fetchRecentAudits(userId, limit: 25);
    final items = <Map<String, dynamic>>[...recentAudits];
    if (includeSample && items.isEmpty) {
      items.add(await fetchSampleAudit());
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
      'sdgAlignment': 'SDG 10.3, 8.5, 16.b',
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
