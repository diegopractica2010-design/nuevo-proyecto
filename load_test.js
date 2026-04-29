/**
 * Load Testing Script - FASE A
 * 
 * Simula carga realista en el sistema:
 * - 10 searches/min = uso normal
 * - 100 searches/min = estrés
 * - 1000 searches/min = límite máximo
 * 
 * Ejecutar: k6 run load_test.js
 * Con opciones: k6 run load_test.js --vus 50 --duration 5m
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE_URL = 'http://localhost:8001';

// Escenarios de carga
export const options = {
  // Ramp-up: 0 a 50 VUs en 2 minutos
  // Estable: 50 VUs por 5 minutos
  // Ramp-down: 50 a 0 VUs en 1 minuto
  stages: [
    { duration: '2m', target: 10 },   // Ramp-up to 10 users
    { duration: '5m', target: 50 },   // Ramp-up to 50 users
    { duration: '10m', target: 50 },  // Stay at 50 for 10 minutes
    { duration: '2m', target: 100 },  // Ramp-up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 for 5 minutes
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  // Límites de error
  thresholds: {
    http_req_duration: ['p(99)<1500', 'p(95)<500'], // 99% < 1.5s, 95% < 0.5s
    http_req_failed: ['rate<0.1'],  // <10% error rate
  },
};

const queries = [
  'leche',
  'pan',
  'huevo',
  'queso',
  'yogur',
  'mantequilla',
  'jamón',
  'atún',
  'arroz',
  'aceite',
];

const stores = ['lider', 'jumbo'];

export default function () {
  const query = queries[Math.floor(Math.random() * queries.length)];
  const store = stores[Math.floor(Math.random() * stores.length)];

  group('Search', () => {
    const response = http.get(
      `${BASE_URL}/search?q=${query}&store=${store}&limit=36`,
      {
        headers: {
          'User-Agent': 'k6-load-test',
        },
      }
    );

    check(response, {
      'status is 200 or 429 (rate limited)': (r) =>
        r.status === 200 || r.status === 429,
      'response time < 2s': (r) => r.timings.duration < 2000,
      'response has results': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.count >= 0;
        } catch {
          return false;
        }
      },
    });

    if (response.status === 429) {
      console.log(`Rate limited! Retry-After: ${response.headers['Retry-After']}`);
    }
  });

  group('Health Check', () => {
    const response = http.get(`${BASE_URL}/health`);
    check(response, {
      'health status is 200': (r) => r.status === 200,
    });
  });

  // Esperar un poco entre requests (simular usuario real)
  sleep(Math.random() * 3);
}
