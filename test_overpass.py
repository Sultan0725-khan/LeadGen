import httpx
import asyncio

async def test_overpass():
    query = """
    [out:json][timeout:25];
    area[name="Berlin"]->.searchArea;
    (
      node[amenity=restaurant](area.searchArea);
      way[amenity=restaurant](area.searchArea);
      relation[amenity=restaurant](area.searchArea);
    );
    out body 10;
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query}
        )
        print(f"Status: {response.status_code}")
        print(f"Response length: {len(response.text)}")
        data = response.json()
        print(f"Elements found: {len(data.get('elements', []))}")
        if data.get('elements'):
            first = data['elements'][0]
            print(f"First element: {first.get('tags', {}).get('name', 'NO NAME')}")

asyncio.run(test_overpass())
