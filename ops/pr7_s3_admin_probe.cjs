// Run ONLY as a separate remote peer in disposable PR7 synthetic storage.
// Empty protobuf requests cannot create/remove an identity even if auth fails.
const http2 = require('node:http2');
if (process.env.PR7_SYNTHETIC_STAGE !== 'explicit-isolated-fixture') {
  throw Error('ISOLATED_SYNTHETIC_STAGE_REQUIRED');
}

async function check(method) {
  const client = http2.connect('http://pr7-target-store:19000');
  try {
    return await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('GRPC_TIMEOUT')), 8000);
      client.once('error', reject);
      const request = client.request({ ':method': 'POST',
        ':path': `/messaging_pb.SeaweedS3IamCache/${method}`,
        'content-type': 'application/grpc', te: 'trailers' });
      let httpStatus, grpcStatus;
      const headers = value => {
        if (value[':status']) httpStatus = Number(value[':status']);
        if (value['grpc-status'] !== undefined) grpcStatus = Number(value['grpc-status']);
      };
      request.on('response', headers);
      request.on('trailers', headers);
      request.on('data', () => {});
      request.once('error', reject);
      request.once('end', () => {
        clearTimeout(timer);
        if (httpStatus !== 200 || grpcStatus !== 16) reject(Error('UNAUTHENTICATED_ADMIN_NOT_REJECTED'));
        else resolve({ method, http_status: httpStatus, grpc_status: grpcStatus });
      });
      request.end(Buffer.from([0, 0, 0, 0, 0]));
    });
  } finally { client.destroy(); }
}

(async () => {
  const results = [];
  for (const method of ['PutIdentity', 'RemoveIdentity', 'PutPolicy', 'DeletePolicy']) results.push(await check(method));
  console.log(JSON.stringify({ status: 'REMOTE_UNAUTHENTICATED_GRPC_ADMIN_REJECTED', results,
    scope: 'SYNTHETIC_EMPTY_REQUESTS_NOT_FULL_AUTHORIZATION_REVIEW' }));
})().catch(error => { console.error(error.message); process.exitCode = 1; });
