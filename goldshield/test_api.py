import requests
import json

print('1. Creating new appraisal...')
files = {'photos': open('d:/goldshield aI/goldshield/photo_store/1/photo_0.jpg', 'rb')}
data = {
    'item_type': 'ring',
    'customer_ref': 'Test_Agent',
    'weight_grams': '10.5',
    'declared_purity': '22K'
}
res = requests.post('http://127.0.0.1:8000/api/appraisal', files=files, data=data)
if not res.ok:
    print('Failed to create:', res.text)
    exit(1)

appraisal_id = res.json()['appraisal_id']
print(f'Created Appraisal ID: {appraisal_id}')

print('2. Running verification (calling Hugging Face API internally)...')
res = requests.post(f'http://127.0.0.1:8000/api/appraisal/{appraisal_id}/verify')
if not res.ok:
    print('Failed to verify:', res.text)
    exit(1)

verify_data = res.json()
model_url = verify_data.get('visual_model_url')
status = verify_data.get('status')

print('\n--- VERIFICATION RESULT ---')
print(f'Status: {status}')
if model_url:
    print(f'SUCCESS! 3D Model URL generated: {model_url}')
else:
    print('FAILED! 3D Model URL is unavailable (InstantMesh timed out).')
